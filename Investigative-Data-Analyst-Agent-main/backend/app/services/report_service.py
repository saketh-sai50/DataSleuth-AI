"""
ReportService: Orchestrates report generation and conversational chat.
"""
import json
from typing import Optional, Any
from sqlalchemy.orm import Session
from loguru import logger

from app.agents.report import ReportAgent
from app.models.report import Report
from app.repositories.report_repository import ReportRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.dataset_repository import DatasetRepository
from app.services.analyst_service import AnalystService
from app.services.investigation_service import _build_llm


def _format_dataset_context_for_chat(ds, analysis) -> str:
    """Format dataset metadata and analysis statistics into clean markdown."""
    lines = []
    lines.append(f"### Dataset File: {ds.filename}")
    lines.append(f"- **Total Row Count (Orders/Items/Entries)**: {ds.row_count}")
    lines.append(f"- **Total Column Count**: {ds.column_count}")

    if analysis.column_types:
        cols_str = ", ".join([f"{col} ({dtype})" for col, dtype in analysis.column_types.items()])
        lines.append(f"- **Columns & Types**: {cols_str}")

    num_aggs = analysis.kpis.get("numeric_agg", {})
    if num_aggs:
        lines.append("- **Numeric Aggregates (Averages, Ranges)**:")
        for col, metrics in num_aggs.items():
            if metrics.get("mean") is not None:
                lines.append(f"  - {col}: Average (Mean)={metrics['mean']:.2f}, Min={metrics['min']}, Max={metrics['max']}")

    top_vals = analysis.kpis.get("top_values", {})
    if top_vals:
        lines.append("- **Top Value Distributions**:")
        for col, counts in top_vals.items():
            top_str = ", ".join([f"'{k}' (count={v})" for k, v in counts.items()])
            lines.append(f"  - {col}: {top_str}")

    if analysis.insights:
        lines.append("- **Key Insights from Data**:")
        for ins in analysis.insights:
            lines.append(f"  - {ins}")

    return "\n".join(lines)


class ReportService:

    """
    Orchestrates report compilation and chat context generation.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._llm = _build_llm()
        self._report_repo = ReportRepository(db)
        self._inv_repo = InvestigationRepository(db)
        self._ds_repo = DatasetRepository(db)
        self._analyst_service = AnalystService()
        self._report_agent = ReportAgent(llm=self._llm)

    def generate_report(self, investigation_id: int) -> Report:
        """
        Generate and persist a business report for an investigation.
        Automatically generates multiple charts via SQL queries (pie + bar per categorical column).
        Marks the investigation status as COMPLETED.
        """
        investigation = self._inv_repo.get_by_id(investigation_id)
        if not investigation:
            raise ValueError(f"Investigation id={investigation_id} not found.")

        logger.info(f"Generating report for investigation id={investigation_id}")

        # Parse hypotheses / validations / missing datasets
        hypotheses, validations, missing_datasets = [], [], []
        for attr, lst in [
            ("hypotheses_json", hypotheses),
            ("validations_json", validations),
            ("missing_datasets_json", missing_datasets),
        ]:
            raw = getattr(investigation, attr, None)
            if raw:
                try:
                    lst.extend(json.loads(raw))
                except Exception as e:
                    logger.warning(f"Failed to parse {attr}: {e}")

        # Get linked datasets
        dataset_links = self._inv_repo.get_datasets(investigation_id)
        dataset_ids = [lnk.dataset_id for lnk in dataset_links]

        # Run analysis on each dataset (for summary stats, insights)
        analysis_results = []
        for link in dataset_links:
            try:
                analysis = self._analyst_service.analyze_dataset(
                    dataset_id=link.dataset_id,
                    question=investigation.question,
                    db=self.db,
                    skip_insights=True
                )
                analysis_results.append(analysis.model_dump())
            except Exception as e:
                logger.warning(f"Failed to analyze dataset id={link.dataset_id}: {e}")

        # ── Auto-generate rich charts via SQL ──────────────────────────────────
        # For every categorical column paired with every numeric column, create
        # a bar chart (group-by sum) and a pie chart. Cap at 6 charts total.
        auto_charts = []
        try:
            import duckdb
            import pandas as pd
            import re
            import plotly.express as px

            conn = duckdb.connect()
            for link in dataset_links:
                ds = self._ds_repo.get_by_id(link.dataset_id)
                if not ds:
                    continue
                try:
                    df = pd.read_csv(ds.file_path) if ds.file_path.endswith(".csv") else \
                         pd.read_excel(ds.file_path, engine="openpyxl")
                except Exception as e:
                    logger.warning(f"Failed to load {ds.filename} for chart gen: {e}")
                    continue

                tbl = re.sub(r"[^a-zA-Z0-9_]", "_", ds.filename.rsplit(".", 1)[0])
                conn.register(tbl, df)

                numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                cat_cols = [
                    c for c in df.columns
                    if not pd.api.types.is_numeric_dtype(df[c])
                    and df[c].nunique() <= 30          # skip high-cardinality text
                    and df[c].nunique() >= 2
                ]

                for cat_col in cat_cols[:3]:           # max 3 cat cols
                    for num_col in numeric_cols[:2]:   # max 2 numeric cols
                        if len(auto_charts) >= 6:
                            break
                        try:
                            sql = (f"SELECT \"{cat_col}\", SUM(\"{num_col}\") AS total "
                                   f"FROM {tbl} GROUP BY \"{cat_col}\" ORDER BY total DESC LIMIT 10")
                            rows = conn.execute(sql).fetchall()
                            if not rows:
                                continue
                            labels = [str(r[0]) for r in rows]
                            values = [float(r[1]) for r in rows]

                            # Pie chart
                            fig_pie = px.pie(
                                names=labels, values=values,
                                title=f"{num_col} share by {cat_col}"
                            )
                            auto_charts.append(json.loads(fig_pie.to_json()))

                            # Bar chart (totals)
                            if len(auto_charts) < 6:
                                fig_bar = px.bar(
                                    x=labels, y=values,
                                    title=f"Total {num_col} by {cat_col}",
                                    labels={"x": cat_col, "y": num_col}
                                )
                                auto_charts.append(json.loads(fig_bar.to_json()))
                        except Exception as e:
                            logger.warning(f"SQL chart gen failed ({cat_col}/{num_col}): {e}")
                    if len(auto_charts) >= 6:
                        break
            conn.close()
        except Exception as e:
            logger.warning(f"Auto chart generation failed: {e}")

        # Fallback: use single pandas chart from analysis if no SQL charts
        if not auto_charts:
            for res in analysis_results:
                if res.get("chart_json"):
                    try:
                        auto_charts.append(json.loads(res["chart_json"]))
                    except Exception:
                        pass

        # Generate report text via Agent
        report_data = self._report_agent.generate_report(
            question=investigation.question,
            hypotheses=hypotheses,
            validations=validations,
            analysis_results=analysis_results,
            missing_datasets=missing_datasets
        )

        creation_data = {
            "executive_summary": report_data.get("executive_summary", ""),
            "root_causes_json": json.dumps(report_data.get("root_causes", [])),
            "evidence_json": json.dumps(report_data.get("evidence", [])),
            "limitations_json": json.dumps(report_data.get("limitations", [])),
            "recommendations_json": json.dumps(report_data.get("recommendations", [])),
            "missing_info_json": json.dumps(report_data.get("missing_info", [])),
            "next_steps_json": json.dumps(report_data.get("next_steps", [])),
            "overall_confidence": float(report_data.get("overall_confidence", 0.0)),
            "charts_json": json.dumps(auto_charts),
        }

        report = self._report_repo.create(investigation_id, creation_data)
        investigation.report_id = report.id
        from app.models.investigation import InvestigationStatus
        self._inv_repo.update_status(investigation_id, InvestigationStatus.COMPLETED.value)
        self.db.commit()

        logger.info(f"Investigation id={investigation_id} completed. Report id={report.id}. Charts: {len(auto_charts)}")
        return report


    def _execute_duckdb_query(self, sql_query: str, dataset_ids: list[int]) -> list[dict[str, Any]]:
        """
        Executes a SQL query on the specified datasets using DuckDB.
        Loads each file using pandas first, then registers them as a view.
        """
        import duckdb
        import pandas as pd
        import re

        conn = duckdb.connect(database=":memory:")
        try:
            for ds_id in dataset_ids:
                ds = self._ds_repo.get_by_id(ds_id)
                if ds:
                    # Clean filename to valid SQL table name (e.g. orders.csv -> orders)
                    name = re.sub(r"[^a-zA-Z0-9_]", "_", ds.filename.split(".")[0])
                    suffix = ds.filename.split(".")[-1].lower()
                    if suffix == "csv":
                        df = pd.read_csv(ds.file_path)
                    else:
                        df = pd.read_excel(ds.file_path, engine="openpyxl")
                    
                    conn.register(name, df)
                    logger.info(f"Registered view '{name}' in DuckDB")
            
            # Execute query
            logger.info(f"Running SQL query on DuckDB: {sql_query}")
            res = conn.execute(sql_query).fetchall()
            cols = [desc[0] for desc in conn.description]
            return [dict(zip(cols, row)) for row in res]
        except Exception as e:
            logger.warning(f"DuckDB SQL execution failed: {e}")
            raise e
        finally:
            conn.close()

    def _generate_sql_query(self, message: str, dataset_ids: list[int]) -> str:
        """
        Calls the LLM to generate a DuckDB SQL query to answer the user's message.
        Returns 'NO_SQL' if no query is needed.
        """
        if self._llm is None:
            return "NO_SQL"

        # Build table schemas description
        import re
        schemas_desc = []
        for ds_id in dataset_ids:
            ds = self._ds_repo.get_by_id(ds_id)
            if ds:
                name = re.sub(r"[^a-zA-Z0-9_]", "_", ds.filename.split(".")[0])
                schema_dict = {}
                if ds.schema_info:
                    try:
                        schema_dict = json.loads(ds.schema_info)
                    except Exception:
                        pass
                cols_desc = ", ".join([f"{col} ({dtype})" for col, dtype in schema_dict.items()])
                schemas_desc.append(f"- Table '{name}': columns: {cols_desc}")

        table_schemas = "\n".join(schemas_desc)

        prompt_text = f"""You are a SQL generator for a DuckDB database.
The user has asked: {message}

We have the following tables available in the database:
{table_schemas}

If the question requires querying the tables to answer (e.g. counting rows, summing values, getting averages, joining tables, filtering, finding top categories, etc.), write a single DuckDB SQL query to get the answer.
If the question is conversational, general, or does not require querying the tables (e.g. 'explain what this means', 'hello', 'what is the plan', 'give recommendations'), respond ONLY with the exact text: NO_SQL

Rules:
1. Table names must be exactly as provided above.
2. Columns must match the columns listed in the schema.
3. Keep the query simple and efficient. Use standard aggregations (COUNT, SUM, AVG, MIN, MAX, GROUP BY, ORDER BY, LIMIT).
4. For string matching, use LIKE or lower() to make it case-insensitive if needed.
5. DO NOT filter too aggressively. If the user asks to compare a specific category/group (e.g. 'South region' or a specific product) with others, do NOT filter by that category in a WHERE clause. Instead, select all categories (e.g. using GROUP BY) so they can be compared in the final response.
6. Respond ONLY with the SQL query or the text NO_SQL. No markdown formatting, no code fences, no extra explanations.

"""
        try:
            from langchain_core.messages import HumanMessage
            response = self._llm.invoke([HumanMessage(content=prompt_text)])
            sql = response.content.strip()
            # Strip markdown fences if present
            if sql.startswith("```"):
                sql = sql.split("```")[1]
                if sql.startswith("sql") or sql.startswith("json"):
                    sql = sql[3:]
            return sql.strip()
        except Exception as exc:
            logger.warning(f"Failed to generate SQL query: {exc}")
            return "NO_SQL"

    def chat(
        self,
        message: str,
        investigation_id: Optional[int] = None,
        context: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Runs a contextual chat message against the ReportAgent.
        SQL query results are placed first in context and clearly marked as ground truth.
        Dataset stats are only added when SQL produces no results, preventing LLM
        from mixing approximate averages with exact query values.
        """
        chat_context = context or ""

        if investigation_id:
            investigation = self._inv_repo.get_by_id(investigation_id)
            if investigation:
                chat_context += (
                    f"\nInvestigation Question: {investigation.question}\n"
                    f"Current Investigation Status: {investigation.status}\n"
                )

                # Fetch dataset links
                dataset_links = self._inv_repo.get_datasets(investigation_id)
                dataset_ids = [link.dataset_id for link in dataset_links]

                # ── Step 1: Run SQL query → results go FIRST, labelled as ground truth ──
                sql_results_available = False
                sql_query = self._generate_sql_query(message, dataset_ids)
                if sql_query and sql_query.upper().strip() != "NO_SQL":
                    try:
                        sql_results = self._execute_duckdb_query(sql_query, dataset_ids)
                        if sql_results:
                            chat_context += (
                                f"\n[Database Query Results] ← THESE ARE EXACT NUMBERS. USE THEM DIRECTLY.\n"
                                f"SQL Executed: {sql_query}\n"
                                f"Results:\n{json.dumps(sql_results, indent=2)}\n"
                                f"[END Database Query Results]\n"
                            )
                            sql_results_available = True
                        else:
                            chat_context += f"\n[SQL query returned no rows: {sql_query}]\n"
                    except Exception as e:
                        logger.warning(f"DuckDB failed for '{sql_query}': {e}")
                        chat_context += f"\n[Database query failed: {e}]\n"

                # ── Step 2: Dataset stats only when SQL has no results ──
                # When SQL gives exact numbers, adding pandas averages confuses the LLM.
                if not sql_results_available:
                    for link in dataset_links:
                        ds = self._ds_repo.get_by_id(link.dataset_id)
                        if ds:
                            try:
                                analysis = self._analyst_service.analyze_dataset(
                                    dataset_id=ds.id,
                                    question=message,
                                    db=self.db,
                                    skip_insights=True
                                )
                                formatted_ds = _format_dataset_context_for_chat(ds, analysis)
                                chat_context += f"\n{formatted_ds}\n"
                            except Exception as e:
                                logger.warning(f"Failed to analyze dataset {ds.filename}: {e}")
                                chat_context += (
                                    f"\n### Dataset: {ds.filename}\n"
                                    f"- Rows: {ds.row_count}, Columns: {ds.column_count}\n"
                                )
                else:
                    # Add lightweight schema info (column names only) so LLM understands context
                    for link in dataset_links:
                        ds = self._ds_repo.get_by_id(link.dataset_id)
                        if ds:
                            schema_cols = "unknown"
                            if ds.schema_info:
                                try:
                                    schema_cols = ", ".join(json.loads(ds.schema_info).keys())
                                except Exception:
                                    pass
                            chat_context += (
                                f"\n[Dataset: {ds.filename} | "
                                f"Total rows: {ds.row_count} | "
                                f"Columns: {schema_cols}]\n"
                            )

                # Add report summary if available
                report = self._report_repo.get_by_investigation_id(investigation_id)
                if report:
                    chat_context += f"\nExisting Report Summary: {report.executive_summary}\n"

        logger.info(f"Running chat | context={len(chat_context)} chars | investigation_id={investigation_id}")
        agent_response = self._report_agent.chat(message=message, context=chat_context)

        return {
            "response": agent_response.get("response", ""),
            "investigation_id": investigation_id,
            "suggested_actions": agent_response.get("suggested_actions", [])
        }

