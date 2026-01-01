import os
import asyncio
import traceback
import uvicorn
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Lokale Imports
from config import Config
from models import QueryRequest, QueryResponse, AmbiguityResult, ValidationResult
from database.manager import DatabaseManager
from utils.sql_guard import enforce_known_tables, enforce_safety
from utils.cache import (
    get_cached_schema,
    get_cached_kb,
    get_cached_meanings,
    get_cached_query_result,
    cache_query_result,
    create_query_session,
    get_query_session,
)
from utils.query_optimizer import QueryOptimizer
from llm.generator import OpenAIGenerator

# Thresholds / constants
CONFIDENCE_THRESHOLD_LOW = 0.4

# FastAPI App
app = FastAPI(
    title="Text2SQL mit ChatGPT - Refactored",
    version="2.1.0",
    description="Modulares Text2SQL System mit Ambiguity Detection und Validation"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM Generator initialisieren
llm_generator = OpenAIGenerator(
    api_key=Config.OPENAI_API_KEY,
    model_name=Config.OPENAI_MODEL
)

# Thread Pool für Parallel Processing
executor = ThreadPoolExecutor(max_workers=4)


@app.get("/")
async def root():
    return {
        "message": "Text2SQL API läuft",
        "version": "2.1.0",
        "features": ["Ambiguity Detection", "SQL Validation", "Modular Structure"]
    }


@app.post("/query", response_model=QueryResponse)
async def query_database(request: QueryRequest):
    """
    Hauptendpoint für Text-to-SQL mit:
    1. Ambiguity Detection (optional)
    2. SQL Generation
    3. SQL Validation (optional)
    4. Ausführung
    """
    try:
        print(f"\n{'='*60}")
        print(f"📝 NEUE ANFRAGE: {request.question}")
        print(f"🗄️  Datenbank: {request.database}")
        
        # 1. Datenbank und Kontext laden
        db_path = f"{Config.DATA_DIR}/{request.database}/{request.database}.sqlite"
        
        if not os.path.exists(db_path):
            error_msg = f"Datenbank nicht gefunden: {db_path}"
            print(f"❌ {error_msg}")
            raise FileNotFoundError(error_msg)
        
        print(f"✅ Datenbank gefunden: {db_path}")

        if request.page > 1 and not request.query_id:
            error_msg = "Paging erfordert query_id aus der ersten Anfrage."
            print(f"❌ {error_msg}")
            return QueryResponse(
                question=request.question,
                generated_sql="",
                results=[],
                row_count=0,
                explanation="Paging ohne query_id ist nicht erlaubt.",
                error=error_msg,
            )
        
        # Check cache first (Phase 1: Caching)
        cached_result = None
        if not request.query_id:
            cached_result = get_cached_query_result(request.question, request.database)
            if cached_result and request.page == 1:  # Nur bei Seite 1 cachen
                print("✅ Cache Hit - verwende gecachtes Ergebnis")
                if not cached_result.get("query_id"):
                    db_manager = DatabaseManager(db_path)
                    base_sql = db_manager.normalize_sql_for_paging(
                        cached_result.get("generated_sql", "")
                    )
                    cached_result["generated_sql"] = base_sql
                    cached_result["query_id"] = create_query_session(
                        request.database, base_sql, request.question
                    )
                return QueryResponse(**cached_result)

        db_manager = DatabaseManager(db_path)
        if request.query_id:
            session = get_query_session(request.query_id)
            if not session:
                error_msg = f"Unbekannte query_id: {request.query_id}"
                print(f"❌ {error_msg}")
                return QueryResponse(
                    question=request.question,
                    generated_sql="",
                    results=[],
                    row_count=0,
                    explanation="query_id ist abgelaufen oder unbekannt.",
                    error=error_msg,
                )
            if session.get("database") != request.database:
                error_msg = "query_id passt nicht zur angefragten Datenbank."
                print(f"❌ {error_msg}")
                return QueryResponse(
                    question=request.question,
                    generated_sql="",
                    results=[],
                    row_count=0,
                    explanation="query_id ist ungueltig fuer diese Datenbank.",
                    error=error_msg,
                )

            base_sql = session.get("sql") or ""
            table_columns = db_manager.get_table_columns()

            safety_error = enforce_safety(base_sql)
            table_error = enforce_known_tables(base_sql, table_columns)
            if safety_error or table_error:
                error_msg = safety_error or table_error
                print(f"❌ Server-Side Validation: {error_msg}")
                return QueryResponse(
                    question=request.question,
                    generated_sql=base_sql,
                    results=[],
                    row_count=0,
                    explanation="SQL aus query_id ist unsicher.",
                    error=error_msg,
                    query_id=request.query_id,
                )

            results, paging_info = db_manager.execute_query_with_paging(
                base_sql,
                page=request.page,
                page_size=request.page_size,
            )

            notice_msg = None
            if paging_info["total_pages"] > 1:
                notice_msg = (
                    f"Seite {paging_info['page']} von {paging_info['total_pages']} "
                    f"({paging_info['rows_on_page']} von {paging_info['total_rows']} Zeilen). "
                )
                if paging_info["has_next_page"]:
                    notice_msg += "Weitere Seiten verfügbar. "
                if paging_info["has_previous_page"]:
                    notice_msg += "Vorherige Seite verfügbar."

            return QueryResponse(
                question=request.question,
                generated_sql=base_sql,
                results=results,
                row_count=len(results),
                page=paging_info["page"],
                page_size=paging_info["page_size"],
                total_pages=paging_info["total_pages"],
                total_rows=paging_info["total_rows"],
                has_next_page=paging_info["has_next_page"],
                has_previous_page=paging_info["has_previous_page"],
                notice=notice_msg,
                query_id=request.query_id,
            )
        # Use cached schema/KB (Phase 1: Caching)
        schema = get_cached_schema(db_path)
        table_columns = db_manager.get_table_columns()
        kb_text = get_cached_kb(request.database, Config.DATA_DIR)
        meanings_text = get_cached_meanings(request.database, Config.DATA_DIR)
        
        print(f"✅ Schema geladen ({len(schema)} Zeichen)")
        print(f"✅ KB geladen ({len(kb_text)} Zeichen)")
        print(f"✅ Meanings geladen ({len(meanings_text)} Zeichen)")
        
        # Fehlerprüfung Kontextdateien
        if kb_text.startswith("[FEHLER") or meanings_text.startswith("[FEHLER"):
            error_msg = f"Kontext-Fehler: {kb_text} {meanings_text}"
            print(f"❌ {error_msg}")
            return QueryResponse(
                question=request.question,
                generated_sql="",
                results=[],
                row_count=0,
                explanation="Kontext konnte nicht geladen werden.",
                error=error_msg
            )
        
        # 2. Parallel: Ambiguity Detection + SQL Generation (Phase 1: Parallelization)
        print(f"\n🔍 Starte Ambiguity Detection und SQL Generierung (parallel)...")
        use_react = getattr(request, 'use_react', True)
        
        loop = asyncio.get_event_loop()
        
        # Ambiguity Task
        ambiguity_task = loop.run_in_executor(
            executor,
            llm_generator.check_ambiguity,
            request.question, schema, kb_text, meanings_text
        )
        
        # SQL Generation Task (mit ReAct oder Standard)
        if use_react:
            sql_task = loop.run_in_executor(
                executor,
                llm_generator.generate_sql_with_react_retrieval,
                request.question,
                db_path,
                request.database,
                3  # max_iterations
            )
        else:
            sql_task = loop.run_in_executor(
                executor,
                llm_generator.generate_sql,
                request.question, schema, kb_text, meanings_text
            )
        
        # Wait for both to complete
        ambiguity_result, sql_result = await asyncio.gather(
            ambiguity_task, sql_task, return_exceptions=True
        )
        
        # Handle Ambiguity Result
        ambiguity_obj = None
        ambiguity_notice = None
        if isinstance(ambiguity_result, Exception):
            print(f"⚠️  Ambiguity Check fehlgeschlagen: {ambiguity_result}")
            ambiguity_obj = None
        else:
            try:
                ambiguity_obj = AmbiguityResult(**ambiguity_result)
                if ambiguity_obj.is_ambiguous:
                    print(f"⚠️  Mehrdeutigkeit erkannt: {ambiguity_obj.reason}")
                    for q in ambiguity_obj.questions:
                        print(f"   - {q}")
                    # Statt hart abzubrechen: Hinweis mitschicken, aber fortfahren.
                    ambiguity_notice = (
                        f"Ambiguity: {ambiguity_obj.reason}. "
                        f"Klärungsfragen: {', '.join(ambiguity_obj.questions or [])}"
                    )
                else:
                    print(f"✅ Frage ist eindeutig")
            except Exception as e:
                print(f"⚠️  Ambiguity Result Parsing fehlgeschlagen: {str(e)}")
        
        # Handle SQL Result
        if isinstance(sql_result, Exception):
            error_msg = f"SQL-Generierung fehlgeschlagen: {str(sql_result)}"
            print(f"❌ {error_msg}")
            return QueryResponse(
                question=request.question,
                ambiguity_check=ambiguity_obj,
                generated_sql="",
                results=[],
                row_count=0,
                explanation="SQL-Generierung fehlgeschlagen.",
                error=error_msg
            )
        
        print(f"📊 SQL Generierung Ergebnis:")
        print(f"   Confidence: {sql_result.get('confidence', 0)}")
        print(f"   Explanation: {sql_result.get('explanation', 'N/A')[:100]}...")
        
        # ReAct Metadaten anzeigen
        if use_react and "retrieval_info" in sql_result:
            retrieval_info = sql_result.get("retrieval_info", {})
            print(
                f"   ReAct: {retrieval_info.get('schema_chunks_used', 0)} Schema-Chunks, "
                f"{retrieval_info.get('kb_entries_used', 0)} KB-Einträge verwendet"
            )
        
        user_explanation = sql_result.get("explanation", "")
        generated_sql = sql_result.get("sql")
        confidence = sql_result.get("confidence", 0.0)

        # 2a. Self-Correction bei niedriger Confidence
        if confidence < CONFIDENCE_THRESHOLD_LOW:
            print(
                f"⚠️  Niedrige Confidence ({confidence:.2f}) – starte Self-Correction Loop..."
            )
            try:
                corrected_result = llm_generator.generate_sql_with_correction(
                    request.question,
                    schema,
                    kb_text,
                    meanings_text,
                    max_iterations=2,
                )
                if corrected_result and corrected_result.get("sql"):
                    sql_result = corrected_result
                    user_explanation = sql_result.get("explanation", user_explanation)
                    generated_sql = sql_result.get("sql")
                    confidence = sql_result.get("confidence", confidence)
                    print(
                        f"✅ Self-Correction abgeschlossen nach "
                        f"{sql_result.get('correction_iterations', 1)} Iteration(en). "
                        f"Neue Confidence: {confidence:.2f}"
                    )
                else:
                    print("⚠️  Self-Correction hat keine bessere SQL liefern können.")
            except Exception as e:
                print(f"⚠️  Self-Correction fehlgeschlagen: {str(e)}")

        if not generated_sql:
            error_msg = f"Keine SQL generiert: {sql_result.get('explanation', 'Unbekannter Fehler')}"
            print(f"❌ {error_msg}")
            return QueryResponse(
                question=request.question,
                ambiguity_check=ambiguity_obj,
                generated_sql="",
                results=[],
                row_count=0,
                explanation=user_explanation,
                error=error_msg
            )

        # Normalisiere SQL, damit Paging deterministisch im Backend erfolgt
        generated_sql = db_manager.normalize_sql_for_paging(generated_sql)

        # 3b. Serverside Sicherheits-Checks
        safety_error = enforce_safety(generated_sql)
        table_error = enforce_known_tables(generated_sql, table_columns)
        if safety_error or table_error:
            error_msg = safety_error or table_error
            print(f"❌ Server-Side Validation: {error_msg}")
            return QueryResponse(
                question=request.question,
                ambiguity_check=ambiguity_obj,
                generated_sql=generated_sql,
                explanation=user_explanation,
                results=[],
                row_count=0,
                error=error_msg
            )
        
        print(f"\n📝 Generierte SQL:")
        print(f"   {generated_sql[:200]}{'...' if len(generated_sql) > 200 else ''}")
        
        # 3d. Query Optimization (Phase 3: Query Optimization)
        optimizer = QueryOptimizer(db_path)
        query_plan = optimizer.analyze_query_plan(generated_sql)
        if query_plan.get("full_table_scan") and query_plan.get("suggestions"):
            print(f"⚠️  Query Optimization Hinweise:")
            for suggestion in query_plan["suggestions"]:
                print(f"   - {suggestion}")
        
        # 4. SQL Validation (mit optionaler Self-Correction bei schweren Fehlern)
        print(f"\n✓ Starte SQL Validation...")
        validation_obj = None
        try:
            # Erste Validierung
            validation_result = llm_generator.validate_sql(generated_sql, schema)
            validation_obj = ValidationResult(**validation_result)
            
            if validation_obj.is_valid:
                print(f"✅ SQL ist valide")
            else:
                print(f"⚠️  Validation Warnings ({validation_obj.severity}):")
                for err in validation_obj.errors:
                    print(f"   - {err}")
                
                # Bei schweren Fehlern einen Korrekturversuch starten,
                # anstatt sofort abzubrechen.
                if validation_obj.severity == "high":
                    print(
                        "⚠️  Validation Severity = 'high' – starte SQL-Korrektur "
                        "basierend auf den Fehlern..."
                    )
                    try:
                        corrected_result = llm_generator.generate_sql_with_correction(
                            request.question,
                            schema,
                            kb_text,
                            meanings_text,
                            max_iterations=2,
                        )
                        if corrected_result and corrected_result.get("sql"):
                            sql_result = corrected_result
                            generated_sql = sql_result.get("sql")
                            user_explanation = sql_result.get(
                                "explanation", user_explanation
                            )
                            confidence = sql_result.get("confidence", confidence)
                            
                            # Erneute Validierung nach Korrektur
                            print("🔁 Validiere korrigierte SQL erneut...")
                            validation_result = llm_generator.validate_sql(
                                generated_sql, schema
                            )
                            validation_obj = ValidationResult(**validation_result)
                            
                            if validation_obj.is_valid or validation_obj.severity != "high":
                                print(
                                    f"✅ Korrigierte SQL akzeptiert "
                                    f"(valid={validation_obj.is_valid}, "
                                    f"severity={validation_obj.severity})"
                                )
                            else:
                                error_msg = (
                                    "SQL Validation fehlgeschlagen nach Korrektur: "
                                    + ", ".join(validation_obj.errors)
                                )
                                print(f"❌ {error_msg}")
                                return QueryResponse(
                                    question=request.question,
                                    ambiguity_check=ambiguity_obj,
                                    generated_sql=generated_sql,
                                    validation=validation_obj,
                                    explanation=user_explanation,
                                    results=[],
                                    row_count=0,
                                    error=error_msg,
                                )
                        else:
                            error_msg = (
                                "SQL Validation fehlgeschlagen: "
                                + ", ".join(validation_obj.errors)
                            )
                            print(f"❌ {error_msg}")
                            return QueryResponse(
                                question=request.question,
                                ambiguity_check=ambiguity_obj,
                                generated_sql=generated_sql,
                                validation=validation_obj,
                                explanation=user_explanation,
                                results=[],
                                row_count=0,
                                error=error_msg,
                            )
                    except Exception as e:
                        error_msg = (
                            "SQL Validation fehlgeschlagen (Korrekturfehler): "
                            + str(e)
                        )
                        print(f"❌ {error_msg}")
                        return QueryResponse(
                            question=request.question,
                            ambiguity_check=ambiguity_obj,
                            generated_sql=generated_sql,
                            validation=validation_obj,
                            explanation=user_explanation,
                            results=[],
                            row_count=0,
                            error=error_msg,
                        )
        except Exception as e:
            print(f"⚠️  Validation fehlgeschlagen (wird übersprungen): {str(e)}")
        
        # 5. SQL Ausführen MIT PAGING
        print(f"\n⚡ Führe SQL aus (Seite {request.page}, {request.page_size} Zeilen)...")
        
        results, paging_info = db_manager.execute_query_with_paging(
            generated_sql,
            page=request.page,
            page_size=request.page_size
        )
        
        print(f"✅ Seite {paging_info['page']}/{paging_info['total_pages']} geladen")
        print(f"   Zeilen: {paging_info['rows_on_page']} von {paging_info['total_rows']} insgesamt")
        
        # Notice für Paging
        notice_msg = None
        if paging_info['total_pages'] > 1:
            notice_msg = (
                f"Seite {paging_info['page']} von {paging_info['total_pages']} "
                f"({paging_info['rows_on_page']} von {paging_info['total_rows']} Zeilen). "
            )
            if paging_info['has_next_page']:
                notice_msg += "Weitere Seiten verfügbar. "
            if paging_info['has_previous_page']:
                notice_msg += "Vorherige Seite verfügbar."

        # 6. Ergebnisse zusammenfassen
        summary_text = None
        try:
            summary_text = llm_generator.summarize_results(
                request.question,
                generated_sql,
                results,
                len(results),
                notice_msg,
            )
        except Exception:
            pass

        if not summary_text:
            preview_keys = ", ".join(results[0].keys()) if results else ""
            summary_text = (
                f"Hier die Top {len(results)} Zeilen zu '{request.question}'. "
                f"Spalten: {preview_keys}"
            )

        # Ambiguity-Hinweis in notice einblenden
        if ambiguity_notice:
            notice_msg = (notice_msg or "") + f" Hinweis: {ambiguity_notice}"

        print(f"{'='*60}\n")

        query_id = create_query_session(request.database, generated_sql, request.question)

        # Cache result (nur bei Seite 1)
        result_dict = {
            "question": request.question,
            "ambiguity_check": ambiguity_obj.dict() if ambiguity_obj else None,
            "generated_sql": generated_sql,
            "validation": validation_obj.dict() if validation_obj else None,
            "results": results,
            "row_count": len(results),
            "page": paging_info['page'],
            "page_size": paging_info['page_size'],
            "total_pages": paging_info['total_pages'],
            "total_rows": paging_info['total_rows'],
            "has_next_page": paging_info['has_next_page'],
            "has_previous_page": paging_info['has_previous_page'],
            "notice": notice_msg,
            "summary": summary_text,
            "explanation": user_explanation,
            "query_id": query_id,
        }
        
        # Cache nur bei Seite 1 (um Cache-Hits zu ermöglichen)
        if request.page == 1:
            cache_query_result(request.question, request.database, result_dict)
        
        return QueryResponse(**result_dict)
    
    except FileNotFoundError as e:
        print(f"❌ FileNotFoundError: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        error_msg = f"Interner Fehler: {str(e)}"
        print(f"❌ Exception: {error_msg}")
        print(traceback.format_exc())
        
        return QueryResponse(
            question=request.question,
            generated_sql="",
            results=[],
            row_count=0,
            explanation="Interner Fehler – bitte erneut versuchen.",
            error=error_msg
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
