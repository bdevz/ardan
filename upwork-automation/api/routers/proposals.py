"""
Proposals API router - handles proposal generation and management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from database.connection import get_db
from shared.models import Proposal, ProposalGenerationRequest
from shared.utils import setup_logging
from services.proposal_service import proposal_service

logger = setup_logging("proposals-router")
router = APIRouter()


@router.post("/generate", response_model=Proposal)
async def generate_proposal(
    request: ProposalGenerationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate proposal for a job
    
    Creates a personalized proposal for the specified job using AI-powered content generation.
    
    - **job_id**: UUID of the job to create a proposal for
    - **custom_instructions**: Optional custom instructions to include in the proposal
    - **include_attachments**: Whether to include default portfolio attachments
    
    Returns the generated proposal with content, bid amount, and metadata.
    """
    try:
        return await proposal_service.generate_proposal(db=db, request=request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating proposal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate proposal"
        )


@router.get("/{proposal_id}", response_model=Proposal)
async def get_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific proposal details
    
    Retrieves detailed information for a specific proposal by ID.
    
    - **proposal_id**: UUID of the proposal to retrieve
    """
    try:
        proposal = await proposal_service.get_proposal(db=db, proposal_id=proposal_id)
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found"
            )
        return proposal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting proposal {proposal_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve proposal"
        )


@router.put("/{proposal_id}")
async def update_proposal(
    proposal_id: UUID,
    proposal_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Update proposal content
    
    Updates the content, bid amount, or attachments of an existing proposal.
    
    - **proposal_id**: UUID of the proposal to update
    - **proposal_data**: Dictionary containing fields to update (content, bid_amount, attachments)
    
    Allowed fields:
    - content: Proposal text content
    - bid_amount: Bid amount (numeric)
    - attachments: List of attachment file IDs
    """
    try:
        success = await proposal_service.update_proposal(
            db=db,
            proposal_id=proposal_id,
            proposal_data=proposal_data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found"
            )
        
        return {"message": f"Proposal {proposal_id} updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating proposal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update proposal"
        )


@router.post("/{proposal_id}/regenerate", response_model=Proposal)
async def regenerate_proposal(
    proposal_id: UUID,
    custom_instructions: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate proposal using LLM with new instructions
    
    Creates a new version of the proposal using AI with updated custom instructions.
    The original proposal is updated with the new content and synced to Google Docs.
    
    - **proposal_id**: UUID of the proposal to regenerate
    - **custom_instructions**: Optional new custom instructions for the LLM
    
    Returns the updated proposal with new content, bid amount, and quality score.
    """
    try:
        return await proposal_service.regenerate_proposal(
            db=db,
            proposal_id=proposal_id,
            custom_instructions=custom_instructions
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error regenerating proposal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate proposal"
        )


@router.get("/{proposal_id}/optimize")
async def optimize_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze proposal and provide optimization suggestions
    
    Uses AI to analyze the proposal content and provide specific suggestions
    for improving quality, relevance, and effectiveness.
    
    - **proposal_id**: UUID of the proposal to analyze
    
    Returns optimization suggestions with priority levels and estimated improvement potential.
    """
    try:
        return await proposal_service.optimize_proposal(db=db, proposal_id=proposal_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error optimizing proposal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to optimize proposal"
        )


@router.get("/{proposal_id}/google-doc")
async def get_proposal_google_doc(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get Google Doc information for a proposal
    
    Returns the Google Doc URL and metadata for the proposal document.
    
    - **proposal_id**: UUID of the proposal
    """
    try:
        proposal = await proposal_service.get_proposal(db=db, proposal_id=proposal_id)
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found"
            )
        
        return {
            "proposal_id": proposal_id,
            "google_doc_id": proposal.google_doc_id,
            "google_doc_url": proposal.google_doc_url,
            "last_updated": proposal.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Google Doc info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Google Doc information"
        )