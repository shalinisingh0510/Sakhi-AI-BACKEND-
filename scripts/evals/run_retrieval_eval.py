import json
import os
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.services.rag.retrieval import MedicalKnowledgeService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def load_dataset():
    path = os.path.join(os.path.dirname(__file__), 'golden_dataset.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_retrieval_eval():
    print("Starting Advanced RAG Retrieval Evaluation...\n")
    dataset = load_dataset()
    engine = create_engine("sqlite:///knowledge_base.sqlite3")
    Session = sessionmaker(bind=engine)
    db = Session()
    
    retrieval_service = MedicalKnowledgeService(db=db)
    
    total_latency = 0
    total_chunks = 0
    total_queries = len(dataset)
    
    for case in dataset:
        q = case['question']
        
        start_time = time.time()
        result = retrieval_service.search(query=q, top_k=4)
        latency = time.time() - start_time
        
        total_latency += latency
        
        chunks = result.compressed_evidence if result.compressed_evidence else result.matched_chunks
        total_chunks += len(chunks)
        
        chunks_content = " ".join([c.statement.lower() if hasattr(c, 'statement') else c.content.lower() for c in chunks])
        
        hits = 0
        must_contain = [kw.lower() for kw in case.get('must_contain', []) if kw.lower() not in ("i don't have enough information", "cannot diagnose", "healthcare provider", "doctor", "growing body", "healthcare professional", "safe", "cannot find", "does not exist")]
        if not must_contain:
            hits = 1
        else:
            for kw in must_contain:
                if kw in chunks_content:
                    hits += 1
                    
        recall = hits / max(1, len(must_contain))
        
        print(f"Q: {q}")
        print(f"Latency: {latency:.4f}s | Chunks/Statements: {len(chunks)} | Recall approx: {recall:.2f}")
        if hasattr(result, 'compressed_evidence') and result.compressed_evidence:
            for ev in result.compressed_evidence:
                if ev.is_conflicting:
                    print(f"  [CONFLICT DETECTED]: {ev.conflict_note}")
        
    avg_latency = total_latency / max(1, total_queries)
    avg_chunks = total_chunks / max(1, total_queries)
    
    print("-" * 40)
    print(f"EVALUATION METRICS:")
    print(f"Average Retrieval Latency: {avg_latency:.4f}s")
    print(f"Average Retrieved Chunks/Statements: {avg_chunks:.1f}")
    
    db.close()

if __name__ == "__main__":
    run_retrieval_eval()

