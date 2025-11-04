"""
Cases API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from app.db.database import get_db
from app.models.case import Case, CaseStatus
from app.schemas.case_schema import CaseCreate, CaseUpdate, CaseResponse, CaseListResponse
from app.services.enhanced_judges import EnhancedJudicialPanel

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=CaseResponse, status_code=201)
async def create_case(
    case_data: CaseCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new case submission
    """
    try:
        # Generate case number (simple implementation)
        count = db.query(Case).count()
        case_number = f"CASE-{count + 1:06d}"
        
        # Create case
        db_case = Case(
            case_number=case_number,
            title=case_data.title,
            facts=case_data.facts,
            legal_arguments=case_data.legal_arguments,
            evidence_summary=case_data.evidence_summary,
            plaintiff_claims=case_data.plaintiff_claims,
            defendant_defenses=case_data.defendant_defenses,
            plaintiff=case_data.plaintiff,
            defendant=case_data.defendant,
            case_type=case_data.case_type,
            jurisdiction=case_data.jurisdiction,
            submitted_by=case_data.submitted_by,
            status=CaseStatus.SUBMITTED
        )
        
        db.add(db_case)
        db.commit()
        db.refresh(db_case)
        
        logger.info(f"Created case {db_case.case_number}")
        
        return db_case
        
    except Exception as e:
        logger.error(f"Error creating case: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating case: {str(e)}")


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific case by ID
    """
    db_case = db.query(Case).filter(Case.id == case_id).first()
    
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return db_case


@router.get("/", response_model=CaseListResponse)
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[CaseStatus] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List cases with pagination and filters
    """
    query = db.query(Case)
    
    # Apply filters
    if status:
        query = query.filter(Case.status == status)
    if jurisdiction:
        query = query.filter(Case.jurisdiction == jurisdiction)
    if case_type:
        query = query.filter(Case.case_type == case_type)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    cases = query.order_by(Case.created_at.desc()).offset(offset).limit(page_size).all()
    
    return CaseListResponse(
        total=total,
        cases=cases,
        page=page,
        page_size=page_size
    )


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: int,
    case_update: CaseUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a case
    """
    db_case = db.query(Case).filter(Case.id == case_id).first()
    
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Update fields
    update_data = case_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_case, field, value)
    
    try:
        db.commit()
        db.refresh(db_case)
        logger.info(f"Updated case {db_case.case_number}")
        return db_case
    except Exception as e:
        logger.error(f"Error updating case: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating case: {str(e)}")


@router.delete("/{case_id}")
async def delete_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a case
    """
    db_case = db.query(Case).filter(Case.id == case_id).first()
    
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    try:
        db.delete(db_case)
        db.commit()
        logger.info(f"Deleted case {db_case.case_number}")
        return {"message": "Case deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting case: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting case: {str(e)}")


@router.post("/autonomous", response_model=dict)
async def analyze_with_enhanced_judges(case_data: CaseCreate, db: Session = Depends(get_db)):
    """Submit case to enhanced autonomous judicial panel with structured frameworks"""
    
    # Generate case number
    count = db.query(Case).count()
    case_number = f"CASE-{count + 1:06d}"
    
    db_case = Case(
        title=case_data.title,
        case_number=case_number,
        jurisdiction=case_data.jurisdiction,
        case_type=case_data.case_type,
        case_facts=case_data.facts,
        parties_involved={
            "plaintiff": case_data.plaintiff,
            "defendant": case_data.defendant
        },
        status=CaseStatus.PROCESSING
    )
    
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    
    try:
        logger.info(f"🏛️  Enhanced Panel analyzing case {case_number}")
        
        # Use enhanced panel with frameworks
        panel = EnhancedJudicialPanel()
        result = await panel.hear_case(
            case_data.facts, 
            case_data.jurisdiction, 
            case_data.case_type
        )
        
        db_case.analysis_result = result
        db_case.recommendation = result["consensus"]["final_verdict"]
        db_case.confidence_score = result["consensus"]["agreement_score"] / 3.0
        db_case.status = CaseStatus.ANALYZED
        db_case.analyzed_at = datetime.now()
        
        db.commit()
        db.refresh(db_case)
        
        logger.info(f"✅ Panel decision: {result['consensus']['final_verdict']}")
        
        return {
            "case_id": db_case.id,
            "case_number": case_number,
            "analysis_result": result,
            "recommendation": db_case.recommendation,
            "confidence": db_case.confidence_score,
            "frameworks_used": result.get("frameworks_used", [])
        }
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {str(e)}")
        db_case.status = CaseStatus.ERROR
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))







