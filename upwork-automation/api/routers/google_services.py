"""
API endpoints for Google Services integration
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from api.services.google_services import google_services_manager
from shared.utils import setup_logging

logger = setup_logging("google-services-api")

router = APIRouter(prefix="/api/google", tags=["google-services"])


@router.get("/auth/status")
async def get_auth_status():
    """Get Google services authentication status"""
    try:
        status = google_services_manager.get_auth_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"Failed to get auth status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/refresh")
async def refresh_services():
    """Refresh all Google services with new credentials"""
    try:
        google_services_manager.refresh_all_services()
        return {
            "success": True,
            "message": "Google services refreshed successfully"
        }
    except Exception as e:
        logger.error(f"Failed to refresh services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Google Docs endpoints
@router.post("/docs/create")
async def create_proposal_document(
    title: str,
    content: str,
    job_id: UUID,
    folder_id: Optional[str] = None
):
    """Create a new Google Doc for a proposal"""
    try:
        docs_service = google_services_manager.get_docs_service()
        result = await docs_service.create_proposal_document(
            title=title,
            content=content,
            job_id=job_id,
            folder_id=folder_id
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to create proposal document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/docs/{document_id}")
async def update_proposal_document(
    document_id: str,
    content: str
):
    """Update existing Google Doc with new content"""
    try:
        docs_service = google_services_manager.get_docs_service()
        success = await docs_service.update_proposal_document(
            document_id=document_id,
            content=content
        )
        
        if success:
            return {
                "success": True,
                "message": "Document updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update document")
            
    except Exception as e:
        logger.error(f"Failed to update document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docs/{document_id}")
async def get_document_content(document_id: str):
    """Get content from Google Doc"""
    try:
        docs_service = google_services_manager.get_docs_service()
        result = await docs_service.get_document_content(document_id)
        
        if result:
            return {
                "success": True,
                "data": result
            }
        else:
            raise HTTPException(status_code=404, detail="Document not found")
            
    except Exception as e:
        logger.error(f"Failed to get document content {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docs")
async def list_proposal_documents(folder_id: Optional[str] = None):
    """List all proposal documents"""
    try:
        docs_service = google_services_manager.get_docs_service()
        result = await docs_service.list_proposal_documents(folder_id)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Google Drive endpoints
@router.get("/drive/portfolio")
async def list_portfolio_files(folder_id: Optional[str] = None):
    """List available portfolio files"""
    try:
        drive_service = google_services_manager.get_drive_service()
        result = await drive_service.list_portfolio_files(folder_id)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to list portfolio files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drive/select-attachments")
async def select_relevant_attachments(
    job_requirements: List[str],
    job_description: str = "",
    max_attachments: int = 3
):
    """Select relevant attachments based on job requirements"""
    try:
        drive_service = google_services_manager.get_drive_service()
        result = await drive_service.select_relevant_attachments(
            job_requirements=job_requirements,
            job_description=job_description,
            max_attachments=max_attachments
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to select attachments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drive/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    description: str = Form("")
):
    """Upload file to Google Drive"""
    try:
        drive_service = google_services_manager.get_drive_service()
        
        # Read file content
        file_content = await file.read()
        
        result = await drive_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            mime_type=file.content_type,
            folder_id=folder_id,
            description=description
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drive/download/{file_id}")
async def download_file(file_id: str):
    """Download file from Google Drive"""
    try:
        drive_service = google_services_manager.get_drive_service()
        content = await drive_service.download_file(file_id)
        
        if content:
            return {
                "success": True,
                "data": {
                    "file_id": file_id,
                    "content_size": len(content),
                    "download_url": f"https://drive.google.com/uc?id={file_id}&export=download"
                }
            }
        else:
            raise HTTPException(status_code=404, detail="File not found")
            
    except Exception as e:
        logger.error(f"Failed to download file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drive/create-folder")
async def create_folder(
    folder_name: str,
    parent_folder_id: Optional[str] = None
):
    """Create a new folder in Google Drive"""
    try:
        drive_service = google_services_manager.get_drive_service()
        result = await drive_service.create_folder(
            folder_name=folder_name,
            parent_folder_id=parent_folder_id
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to create folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Google Sheets endpoints
@router.post("/sheets/export/jobs")
async def export_jobs_data(
    jobs_data: List[Dict[str, Any]],
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = "Jobs"
):
    """Export jobs data to Google Sheets"""
    try:
        sheets_service = google_services_manager.get_sheets_service()
        result = await sheets_service.export_jobs_data(
            jobs_data=jobs_data,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to export jobs data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sheets/export/proposals")
async def export_proposals_data(
    proposals_data: List[Dict[str, Any]],
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = "Proposals"
):
    """Export proposals data to Google Sheets"""
    try:
        sheets_service = google_services_manager.get_sheets_service()
        result = await sheets_service.export_proposals_data(
            proposals_data=proposals_data,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to export proposals data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sheets/export/analytics")
async def export_analytics_data(
    analytics_data: Dict[str, Any],
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = "Analytics"
):
    """Export analytics data to Google Sheets"""
    try:
        sheets_service = google_services_manager.get_sheets_service()
        result = await sheets_service.export_analytics_data(
            analytics_data=analytics_data,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to export analytics data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sheets/create-dashboard")
async def create_dashboard_spreadsheet():
    """Create a comprehensive dashboard spreadsheet"""
    try:
        sheets_service = google_services_manager.get_sheets_service()
        result = await sheets_service.create_dashboard_spreadsheet()
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to create dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Utility endpoints
@router.post("/test-integration")
async def test_google_integration():
    """Test Google services integration"""
    try:
        results = {}
        
        # Test Docs service
        try:
            docs_service = google_services_manager.get_docs_service()
            test_doc = await docs_service.create_proposal_document(
                title="Integration Test",
                content="This is a test document created by the integration test.",
                job_id=UUID("12345678-1234-5678-9012-123456789012")
            )
            results['docs'] = {
                "status": "success",
                "document_id": test_doc.get('document_id'),
                "mock": test_doc.get('document_id', '').startswith('mock_')
            }
        except Exception as e:
            results['docs'] = {"status": "error", "error": str(e)}
        
        # Test Drive service
        try:
            drive_service = google_services_manager.get_drive_service()
            portfolio_files = await drive_service.list_portfolio_files()
            results['drive'] = {
                "status": "success",
                "files_found": len(portfolio_files),
                "mock": len(portfolio_files) > 0 and portfolio_files[0].get('id', '').startswith('mock_')
            }
        except Exception as e:
            results['drive'] = {"status": "error", "error": str(e)}
        
        # Test Sheets service
        try:
            sheets_service = google_services_manager.get_sheets_service()
            test_data = [{"id": "test", "title": "Test Job", "status": "TEST"}]
            export_result = await sheets_service.export_jobs_data(test_data)
            results['sheets'] = {
                "status": "success",
                "spreadsheet_id": export_result.get('spreadsheet_id'),
                "mock": export_result.get('spreadsheet_id', '').startswith('mock_')
            }
        except Exception as e:
            results['sheets'] = {"status": "error", "error": str(e)}
        
        # Overall status
        all_success = all(r.get('status') == 'success' for r in results.values())
        
        return {
            "success": all_success,
            "data": {
                "overall_status": "success" if all_success else "partial_failure",
                "services": results,
                "auth_status": google_services_manager.get_auth_status(),
                "test_timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))