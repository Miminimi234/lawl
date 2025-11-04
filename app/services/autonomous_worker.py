"""
Autonomous Legal System - Continuously monitors and analyzes real court cases from CourtListener
"""
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.case import Case, CaseStatus
from app.models.document import Document, DocumentType
from app.services.enhanced_judges import EnhancedJudicialPanel
from app.services.rag_engine import RAGEngine
from app.services.courtlistener_feed import SmartCaseFeed
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutonomousLegalSystem:
    """
    Fully autonomous system that:
    1. Pulls real cases from CourtListener
    2. Automatically analyzes them with structured frameworks
    3. Stores all judicial opinions
    4. Never stops working
    """
    
    def __init__(self, courtlistener_token: str = None):
        self.panel = EnhancedJudicialPanel()
        self.rag = RAGEngine()
        self.case_feed = SmartCaseFeed(courtlistener_token)
        self.running = True
        self.analyzed_citations = set()
    
    async def run_forever(self):
        """Main loop - runs continuously"""
        logger.info("⚖️  AUTONOMOUS JUDICIAL SYSTEM ONLINE")
        logger.info("📡 Connected to CourtListener feed")
        logger.info("🏛️  3 AI judges are now monitoring and analyzing cases...")
        logger.info("")
        
        # Load already analyzed cases
        await self._load_analyzed_citations()
        
        while self.running:
            try:
                # 1. Fetch new cases from CourtListener
                logger.info("📡 Fetching new cases from CourtListener...")
                new_cases = self.case_feed.get_diverse_feed(total_limit=20)
                
                # Filter out already analyzed
                unanalyzed = [
                    c for c in new_cases 
                    if c['citation'] not in self.analyzed_citations
                ]
                
                logger.info(f"📋 Found {len(unanalyzed)} new unanalyzed cases")
                logger.info("")
                
                # 2. Process each case
                for case_data in unanalyzed:
                    # Skip if case text too short
                    if len(case_data['case_text']) < 200:
                        logger.info(f"⏭️  Skipping {case_data['citation']} - insufficient text")
                        continue
                    
                    await self.analyze_case(case_data)
                    self.analyzed_citations.add(case_data['citation'])
                    
                    # Rate limiting
                    await asyncio.sleep(3)
                
                # 3. Wait before next poll (check every 30 minutes)
                logger.info("⏸️  Waiting 30 minutes before next case pull...")
                logger.info("")
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(60)
    
    async def _load_analyzed_citations(self):
        """Load citations of already analyzed cases"""
        db = SessionLocal()
        try:
            cases = db.query(Case).all()
            self.analyzed_citations = {c.case_number for c in cases if c.case_number}
            logger.info(f"📚 Loaded {len(self.analyzed_citations)} previously analyzed cases")
            logger.info("")
        finally:
            db.close()
    
    async def analyze_case(self, case_data: Dict):
        """Automatically analyze a real court case"""
        db = SessionLocal()
        
        try:
            title = case_data['title']
            citation = case_data['citation']
            
            logger.info(f"⚖️  ANALYZING: {title}")
            logger.info(f"   Citation: {citation}")
            logger.info(f"   Court: {case_data['court']}")
            logger.info(f"   Category: {case_data.get('category', 'general')}")
            
            # Create case record
            db_case = Case(
                title=title,
                case_number=citation,
                jurisdiction=case_data['court'],
                case_type=case_data.get('category', 'general'),
                facts=case_data['case_text'],
                status=CaseStatus.PROCESSING
            )
            
            db.add(db_case)
            db.commit()
            db.refresh(db_case)
            
            # Store full opinion as document for RAG
            try:
                doc = Document(
                    title=title,
                    document_type=DocumentType.CASE_LAW,
                    citation=citation,
                    case_name=title,
                    court=case_data['court'],
                    jurisdiction=case_data['court'],
                    full_text=case_data['case_text'],
                    summary=case_data['snippet'],
                    source_url=case_data.get('url', '')
                )
                
                db.add(doc)
                db.commit()
                db.refresh(doc)
                
                # Add to RAG vector store
                uuid = self.rag.add_document({
                    "title": title,
                    "citation": citation,
                    "content": case_data['case_text'],
                    "court": case_data['court'],
                    "jurisdiction": case_data['court'],
                    "doc_type": 'case_law',
                    "summary": case_data['snippet']
                })
                
                doc.weaviate_id = uuid
                db.commit()
                
                logger.info(f"   ✅ Added to vector database")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not add to vector DB: {e}")
            
            # Convene enhanced judges with structured frameworks
            logger.info(f"   🏛️  Convening three-judge panel with legal frameworks...")
            
            result = await self.panel.hear_case(
                case_facts=case_data['case_text'],
                jurisdiction=case_data['court'],
                case_type=case_data.get('category', 'general')
            )
            
            # Store results
            db_case.analysis_result = result
            db_case.recommendation = result['consensus']['final_verdict']
            db_case.confidence_score = result['consensus']['agreement_score'] / 3.0
            db_case.status = CaseStatus.ANALYZED
            db_case.analyzed_at = datetime.now()
            db.commit()
            
            logger.info(f"✅ COMPLETED: {title}")
            logger.info(f"   Verdict: {result['consensus']['final_verdict'][:100]}...")
            logger.info(f"   Agreement: {result['consensus']['agreement_score']}/3 judges")
            logger.info(f"   Frameworks: {', '.join(result.get('frameworks_used', []))}")
            logger.info("")
            
        except Exception as e:
            logger.error(f"❌ Error analyzing case: {e}")
            if 'db_case' in locals():
                db_case.status = CaseStatus.SUBMITTED  # Keep as submitted if analysis fails
                db.commit()
        finally:
            db.close()
    
    def stop(self):
        """Gracefully stop the system"""
        logger.info("🛑 Shutting down autonomous system...")
        self.running = False


# Entry point
async def main():
    # Optional: Add your CourtListener API token here for higher rate limits
    # Get token from: https://www.courtlistener.com/api/rest-info/
    import os
    COURTLISTENER_TOKEN = os.getenv('COURTLISTENER_API_TOKEN')
    
    system = AutonomousLegalSystem(courtlistener_token=COURTLISTENER_TOKEN)
    try:
        await system.run_forever()
    except KeyboardInterrupt:
        system.stop()

if __name__ == "__main__":
    asyncio.run(main())






