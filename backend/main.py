import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Lokale Imports
from config import Config
from models import QueryRequest, QueryResponse, AmbiguityResult, ValidationResult
from database.manager import DatabaseManager
from utils.context_loader import load_context_files
from utils.sql_guard import enforce_known_tables, enforce_safety
from llm.generator import OpenAIGenerator

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
        
        db_manager = DatabaseManager(db_path)
        schema = db_manager.get_schema_and_sample()
        table_columns = db_manager.get_table_columns()
        kb_text, meanings_text = load_context_files(request.database, Config.DATA_DIR)
        
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
        
        # 2. Ambiguity Detection (non-blocking)
        print(f"\n🔍 Starte Ambiguity Detection...")
        ambiguity_obj = None
        try:
            ambiguity_result = llm_generator.check_ambiguity(
                request.question, schema, kb_text, meanings_text
            )
            ambiguity_obj = AmbiguityResult(**ambiguity_result)
            
            if ambiguity_obj.is_ambiguous:
                print(f"⚠️  Mehrdeutigkeit erkannt: {ambiguity_obj.reason}")
                for q in ambiguity_obj.questions:
                    print(f"   - {q}")
            else:
                print(f"✅ Frage ist eindeutig")
        except Exception as e:
            print(f"⚠️  Ambiguity Check fehlgeschlagen (wird übersprungen): {str(e)}")
        
        # 3. SQL Generation (immer ausführen!)
        print(f"\n🤖 Starte SQL Generierung...")
        sql_result = llm_generator.generate_sql(
            request.question, schema, kb_text, meanings_text
        )
        
        print(f"📊 SQL Generierung Ergebnis:")
        print(f"   Confidence: {sql_result.get('confidence', 0)}")
        print(f"   Explanation: {sql_result.get('explanation', 'N/A')[:100]}...")

        user_explanation = sql_result.get("explanation", "")
        generated_sql = sql_result.get("sql")

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
                results=[],
                row_count=0,
                error=error_msg
            )
        
        print(f"\n📝 Generierte SQL:")
        print(f"   {generated_sql[:200]}{'...' if len(generated_sql) > 200 else ''}")
        
        # 4. SQL Validation (non-blocking)
        print(f"\n✓ Starte SQL Validation...")
        validation_obj = None
        try:
            validation_result = llm_generator.validate_sql(generated_sql, schema)
            validation_obj = ValidationResult(**validation_result)
            
            if validation_obj.is_valid:
                print(f"✅ SQL ist valide")
            else:
                print(f"⚠️  Validation Warnings ({validation_obj.severity}):")
                for err in validation_obj.errors:
                    print(f"   - {err}")
                
                # Nur bei "high" severity abbrechen
                if validation_obj.severity == "high":
                    error_msg = f"SQL Validation fehlgeschlagen: {', '.join(validation_obj.errors)}"
                    print(f"❌ {error_msg}")
                    return QueryResponse(
                        question=request.question,
                        ambiguity_check=ambiguity_obj,
                        generated_sql=generated_sql,
                        validation=validation_obj,
                        explanation=user_explanation,
                        results=[],
                        row_count=0,
                        error=error_msg
                    )
        except Exception as e:
            print(f"⚠️  Validation fehlgeschlagen (wird übersprungen): {str(e)}")
        
        # 5. SQL Ausführen
        print(f"\n⚡ Führe SQL aus...")
        results, truncated = db_manager.execute_query(
            generated_sql, max_rows=Config.MAX_RESULT_ROWS
        )
        notice_msg = None
        if truncated:
            notice_msg = (
                f"Ergebnis wurde auf {Config.MAX_RESULT_ROWS} Zeilen gekürzt, "
                "weitere Zeilen wurden aus Performance-Gründen unterdrückt."
            )
            print(f"⚠️  Ergebnis gekürzt: {notice_msg}")

        print(f"✅ Erfolgreich! {len(results)} Zeilen zurückgegeben")

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

        print(f"{'='*60}\n")

        return QueryResponse(
            question=request.question,
            ambiguity_check=ambiguity_obj,
            generated_sql=generated_sql,
            validation=validation_obj,
            results=results,
            row_count=len(results),
            notice=notice_msg,
            summary=summary_text,
            explanation=user_explanation,
        )
    
    except FileNotFoundError as e:
        print(f"❌ FileNotFoundError: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        error_msg = f"Interner Fehler: {str(e)}"
        print(f"❌ Exception: {error_msg}")
        import traceback
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)