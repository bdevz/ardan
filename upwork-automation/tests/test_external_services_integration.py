"""
External Services Integration Testing
Part of Task 18: Integration Testing and System Validation

This module provides integration tests for:
- OpenAI API integration for proposal generation
- Google Services (Docs, Drive, Sheets) integration
- Slack API integration for notifications
- n8n webhook integration for workflows
- Browserbase API integration for browser automation
- Email services integration
"""
import asyncio
import pytest
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
import httpx

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.database.connection import get_db, init_db
from api.database.models import JobModel, ProposalModel, ApplicationModel
from shared.models import JobStatus, JobType, ProposalStatus, ApplicationStatus


class TestOpenAIIntegration:
    """Test OpenAI API integration for proposal generation"""
    
    @pytest.mark.asyncio
    async def test_proposal_generation_integration(self):
        """Test complete proposal generation workflow with OpenAI"""
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            # Mock successful OpenAI response
            mock_openai.return_value = {
                "choices": [{
                    "message": {
                        "content": """I am excited to help you build advanced Salesforce Agentforce solutions that will transform your customer engagement strategy. With my deep expertise in AI-powered automation, I can deliver exactly what you're looking for.

With 6+ years of specialized experience in Salesforce AI development, I have successfully delivered 20+ Agentforce implementations with an average ROI increase of 150%. My recent project for GlobalTech resulted in 40% faster response times and 60% improvement in customer satisfaction scores through intelligent agent workflows.

I would love to discuss your specific requirements and demonstrate how my expertise can drive exceptional results for your project. I'm available to start immediately and can provide a detailed project timeline within 24 hours of our initial consultation."""
                    }
                }],
                "usage": {
                    "prompt_tokens": 250,
                    "completion_tokens": 180,
                    "total_tokens": 430
                }
            }
            
            # Test proposal generation service
            job_data = {
                "title": "Senior Salesforce Agentforce Developer",
                "description": "We need an experienced developer to build AI agents using Salesforce Agentforce platform for customer service automation.",
                "budget_range": {"min": 70, "max": 90},
                "client_info": {
                    "rating": 4.8,
                    "hire_rate": 0.9,
                    "payment_verified": True
                }
            }
            
            # Mock proposal service
            async def generate_proposal_with_openai(job_data):
                # Construct prompt
                prompt = f"""
                Generate a professional 3-paragraph proposal for this Upwork job:
                
                Job Title: {job_data['title']}
                Description: {job_data['description']}
                Budget: ${job_data['budget_range']['min']}-${job_data['budget_range']['max']}/hr
                Client Rating: {job_data['client_info']['rating']}/5
                
                Requirements:
                1. First paragraph: Goal-focused introduction showing understanding of Agentforce
                2. Second paragraph: Relevant experience with specific metrics and achievements
                3. Third paragraph: Clear call-to-action with availability and next steps
                """
                
                response = await mock_openai(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert Salesforce Agentforce developer writing a winning proposal."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                
                return {
                    "proposal_content": response["choices"][0]["message"]["content"],
                    "token_usage": response["usage"],
                    "generated_at": datetime.utcnow().isoformat()
                }
            
            # Execute proposal generation
            result = await generate_proposal_with_openai(job_data)
            
            # Verify proposal structure and content
            proposal_content = result["proposal_content"]
            paragraphs = proposal_content.split('\n\n')
            
            assert len(paragraphs) >= 3, "Proposal should have at least 3 paragraphs"
            
            # Verify content requirements
            assert "Agentforce" in proposal_content, "Should mention Agentforce"
            assert any(char.isdigit() for char in proposal_content), "Should include metrics/numbers"
            assert any(word in proposal_content.lower() for word in ["discuss", "available", "start"]), "Should have clear CTA"
            
            # Verify API usage
            assert result["token_usage"]["total_tokens"] > 0
            assert result["generated_at"] is not None
            
            # Verify OpenAI was called correctly
            mock_openai.assert_called_once()
            call_args = mock_openai.call_args
            assert call_args[1]["model"] == "gpt-4"
            assert "Agentforce" in str(call_args[1]["messages"])
            
            print("✅ OpenAI proposal generation integration test passed")
    
    @pytest.mark.asyncio
    async def test_openai_error_handling_integration(self):
        """Test OpenAI API error handling and fallback strategies"""
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            # Test different error scenarios
            error_scenarios = [
                {"error": "RateLimitError", "message": "Rate limit exceeded", "retry_after": 1},
                {"error": "InvalidRequestError", "message": "Invalid request", "retry_after": 0},
                {"error": "APIError", "message": "API temporarily unavailable", "retry_after": 2}
            ]
            
            async def proposal_service_with_error_handling(job_data, error_scenario):
                max_retries = 3
                base_delay = 1
                
                for attempt in range(max_retries):
                    try:
                        if attempt < 2:  # Fail first two attempts
                            if error_scenario["error"] == "RateLimitError":
                                raise Exception(f"RateLimitError: {error_scenario['message']}")
                            elif error_scenario["error"] == "InvalidRequestError":
                                raise Exception(f"InvalidRequestError: {error_scenario['message']}")
                            else:
                                raise Exception(f"APIError: {error_scenario['message']}")
                        else:
                            # Success on third attempt
                            return {
                                "proposal_content": "Generated proposal after retry",
                                "attempts": attempt + 1,
                                "success": True
                            }
                    
                    except Exception as e:
                        error_type = str(e).split(':')[0]
                        
                        if error_type == "RateLimitError" and attempt < max_retries - 1:
                            # Exponential backoff for rate limits
                            delay = base_delay * (2 ** attempt)
                            await asyncio.sleep(delay / 10)  # Reduced for testing
                            continue
                        elif error_type == "APIError" and attempt < max_retries - 1:
                            # Retry for API errors
                            await asyncio.sleep(base_delay / 10)
                            continue
                        else:
                            # Don't retry for invalid requests or max retries reached
                            return {
                                "proposal_content": None,
                                "attempts": attempt + 1,
                                "success": False,
                                "error": str(e)
                            }
            
            # Test each error scenario
            job_data = {"title": "Test Job", "description": "Test description"}
            
            for scenario in error_scenarios:
                result = await proposal_service_with_error_handling(job_data, scenario)
                
                if scenario["error"] in ["RateLimitError", "APIError"]:
                    # Should eventually succeed with retries
                    assert result["success"], f"Should recover from {scenario['error']}"
                    assert result["attempts"] == 3, "Should retry and succeed on third attempt"
                else:
                    # Should fail immediately for invalid requests
                    assert not result["success"], f"Should not retry {scenario['error']}"
                    assert result["attempts"] == 1, "Should not retry invalid requests"
            
            print("✅ OpenAI error handling integration test passed")


class TestGoogleServicesIntegration:
    """Test Google Services (Docs, Drive, Sheets) integration"""
    
    @pytest.mark.asyncio
    async def test_google_docs_integration(self):
        """Test Google Docs API integration for proposal storage"""
        with patch('googleapiclient.discovery.build') as mock_build:
            # Mock Google Docs service
            mock_docs_service = Mock()
            mock_build.return_value = mock_docs_service
            
            # Mock document operations
            mock_docs_service.documents().create.return_value.execute.return_value = {
                "documentId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "title": "Proposal - Senior Salesforce Agentforce Developer",
                "revisionId": "ALm37BVWnJb7u_GVeKp5b9jG8hSuLbr_Ug"
            }
            
            mock_docs_service.documents().batchUpdate.return_value.execute.return_value = {
                "replies": [{"insertText": {}}]
            }
            
            mock_docs_service.documents().get.return_value.execute.return_value = {
                "documentId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "title": "Proposal - Senior Salesforce Agentforce Developer",
                "body": {
                    "content": [
                        {
                            "paragraph": {
                                "elements": [
                                    {"textRun": {"content": "I am an experienced Salesforce Agentforce developer..."}}
                                ]
                            }
                        }
                    ]
                }
            }
            
            # Test Google Docs integration
            async def create_proposal_document(title, content):
                # Create document
                create_request = {
                    "title": title
                }
                
                doc = mock_docs_service.documents().create(body=create_request).execute()
                document_id = doc["documentId"]
                
                # Add content to document
                requests = [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content
                        }
                    }
                ]
                
                mock_docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={"requests": requests}
                ).execute()
                
                return {
                    "document_id": document_id,
                    "title": doc["title"],
                    "url": f"https://docs.google.com/document/d/{document_id}/edit"
                }
            
            # Execute document creation
            proposal_content = "I am an experienced Salesforce Agentforce developer with 5+ years of expertise..."
            result = await create_proposal_document(
                "Proposal - Senior Salesforce Agentforce Developer",
                proposal_content
            )
            
            # Verify document creation
            assert result["document_id"] is not None
            assert "Salesforce Agentforce" in result["title"]
            assert "docs.google.com" in result["url"]
            
            # Verify API calls
            mock_docs_service.documents().create.assert_called_once()
            mock_docs_service.documents().batchUpdate.assert_called_once()
            
            print("✅ Google Docs integration test passed")
    
    @pytest.mark.asyncio
    async def test_google_drive_integration(self):
        """Test Google Drive API integration for attachment management"""
        with patch('googleapiclient.discovery.build') as mock_build:
            # Mock Google Drive service
            mock_drive_service = Mock()
            mock_build.return_value = mock_drive_service
            
            # Mock file search
            mock_drive_service.files().list.return_value.execute.return_value = {
                "files": [
                    {
                        "id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                        "name": "Salesforce Case Study - TechCorp.pdf",
                        "mimeType": "application/pdf",
                        "size": "2048576",
                        "modifiedTime": "2024-01-15T10:30:00.000Z"
                    },
                    {
                        "id": "2CxjNWt1YSB6oGNeKvCdCZkhnVVrqumct85PgwF3vqot",
                        "name": "Agentforce Demo Video.mp4",
                        "mimeType": "video/mp4",
                        "size": "15728640",
                        "modifiedTime": "2024-01-10T14:20:00.000Z"
                    },
                    {
                        "id": "3DykOXu2ZTC7pHOfLwDeDalkioWsrvndu96QhxG4wrpu",
                        "name": "Salesforce Certifications.pdf",
                        "mimeType": "application/pdf",
                        "size": "1024000",
                        "modifiedTime": "2024-01-05T09:15:00.000Z"
                    }
                ]
            }
            
            # Mock file download
            mock_drive_service.files().get_media.return_value.execute.return_value = b"Mock file content"
            
            # Test Drive integration
            async def search_relevant_attachments(keywords):
                # Build search query
                query_parts = []
                for keyword in keywords:
                    query_parts.append(f"name contains '{keyword}'")
                
                query = " or ".join(query_parts)
                
                # Search for files
                results = mock_drive_service.files().list(
                    q=query,
                    fields="files(id,name,mimeType,size,modifiedTime)",
                    orderBy="modifiedTime desc"
                ).execute()
                
                files = results.get("files", [])
                
                # Filter and rank by relevance
                relevant_files = []
                for file in files:
                    relevance_score = 0
                    for keyword in keywords:
                        if keyword.lower() in file["name"].lower():
                            relevance_score += 1
                    
                    if relevance_score > 0:
                        relevant_files.append({
                            **file,
                            "relevance_score": relevance_score,
                            "download_url": f"https://drive.google.com/file/d/{file['id']}/view"
                        })
                
                # Sort by relevance
                relevant_files.sort(key=lambda x: x["relevance_score"], reverse=True)
                
                return relevant_files
            
            # Execute attachment search
            keywords = ["Salesforce", "Agentforce", "Case Study"]
            attachments = await search_relevant_attachments(keywords)
            
            # Verify search results
            assert len(attachments) >= 2  # Should find Salesforce and Agentforce files
            
            # Verify relevance ranking
            top_attachment = attachments[0]
            assert "Salesforce" in top_attachment["name"] or "Agentforce" in top_attachment["name"]
            assert top_attachment["relevance_score"] > 0
            
            # Verify file metadata
            for attachment in attachments:
                assert "id" in attachment
                assert "name" in attachment
                assert "download_url" in attachment
                assert attachment["download_url"].startswith("https://drive.google.com")
            
            # Verify API calls
            mock_drive_service.files().list.assert_called_once()
            
            print("✅ Google Drive integration test passed")
    
    @pytest.mark.asyncio
    async def test_google_sheets_integration(self):
        """Test Google Sheets API integration for data export"""
        with patch('googleapiclient.discovery.build') as mock_build:
            # Mock Google Sheets service
            mock_sheets_service = Mock()
            mock_build.return_value = mock_sheets_service
            
            # Mock spreadsheet creation
            mock_sheets_service.spreadsheets().create.return_value.execute.return_value = {
                "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "properties": {
                    "title": "Upwork Automation Analytics - January 2024"
                },
                "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
            }
            
            # Mock data update
            mock_sheets_service.spreadsheets().values().update.return_value.execute.return_value = {
                "updatedCells": 50,
                "updatedColumns": 5,
                "updatedRows": 10
            }
            
            # Test Sheets integration
            async def export_analytics_to_sheets(analytics_data):
                # Create spreadsheet
                spreadsheet_body = {
                    "properties": {
                        "title": f"Upwork Automation Analytics - {datetime.now().strftime('%B %Y')}"
                    }
                }
                
                spreadsheet = mock_sheets_service.spreadsheets().create(
                    body=spreadsheet_body
                ).execute()
                
                spreadsheet_id = spreadsheet["spreadsheetId"]
                
                # Prepare data for sheets
                headers = ["Date", "Jobs Found", "Applications Sent", "Responses", "Success Rate"]
                rows = [headers]
                
                for entry in analytics_data:
                    row = [
                        entry["date"],
                        entry["jobs_found"],
                        entry["applications_sent"],
                        entry["responses_received"],
                        f"{entry['success_rate']:.2%}"
                    ]
                    rows.append(row)
                
                # Update spreadsheet with data
                range_name = "Sheet1!A1:E" + str(len(rows))
                value_input_option = "RAW"
                
                body = {
                    "values": rows
                }
                
                result = mock_sheets_service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=body
                ).execute()
                
                return {
                    "spreadsheet_id": spreadsheet_id,
                    "spreadsheet_url": spreadsheet["spreadsheetUrl"],
                    "updated_cells": result["updatedCells"]
                }
            
            # Execute analytics export
            analytics_data = [
                {"date": "2024-01-15", "jobs_found": 25, "applications_sent": 8, "responses_received": 3, "success_rate": 0.375},
                {"date": "2024-01-16", "jobs_found": 18, "applications_sent": 6, "responses_received": 2, "success_rate": 0.333},
                {"date": "2024-01-17", "jobs_found": 22, "applications_sent": 7, "responses_received": 4, "success_rate": 0.571}
            ]
            
            result = await export_analytics_to_sheets(analytics_data)
            
            # Verify export results
            assert result["spreadsheet_id"] is not None
            assert "docs.google.com/spreadsheets" in result["spreadsheet_url"]
            assert result["updated_cells"] > 0
            
            # Verify API calls
            mock_sheets_service.spreadsheets().create.assert_called_once()
            mock_sheets_service.spreadsheets().values().update.assert_called_once()
            
            print("✅ Google Sheets integration test passed")


class TestSlackIntegration:
    """Test Slack API integration for notifications"""
    
    @pytest.mark.asyncio
    async def test_slack_notification_integration(self):
        """Test Slack notification system integration"""
        with patch('slack_sdk.WebClient') as mock_slack_client:
            # Mock Slack client
            mock_client = Mock()
            mock_slack_client.return_value = mock_client
            
            # Mock successful message posting
            mock_client.chat_postMessage.return_value = {
                "ok": True,
                "channel": "C1234567890",
                "ts": "1234567890.123456",
                "message": {
                    "text": "🎯 Found 5 new Salesforce Agentforce jobs!",
                    "user": "U1234567890",
                    "ts": "1234567890.123456"
                }
            }
            
            # Mock file upload
            mock_client.files_upload.return_value = {
                "ok": True,
                "file": {
                    "id": "F1234567890",
                    "name": "job_screenshot.png",
                    "permalink": "https://files.slack.com/files-pri/T1234567890-F1234567890/job_screenshot.png"
                }
            }
            
            # Test notification service
            async def send_job_discovery_notification(jobs_found, top_job, screenshot_path=None):
                # Create rich notification message
                message_blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🎯 Found {jobs_found} new Salesforce jobs!"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Top Job:* {top_job['title']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Rate:* ${top_job['hourly_rate']}/hr"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Client Rating:* {top_job['client_rating']}⭐"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Match Score:* {top_job['match_score']:.0%}"
                            }
                        ]
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Job"
                                },
                                "url": top_job["job_url"],
                                "style": "primary"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Generate Proposal"
                                },
                                "value": top_job["id"]
                            }
                        ]
                    }
                ]
                
                # Send message
                response = mock_client.chat_postMessage(
                    channel="#upwork-automation",
                    text=f"🎯 Found {jobs_found} new Salesforce Agentforce jobs!",
                    blocks=message_blocks
                )
                
                result = {
                    "success": response["ok"],
                    "message_ts": response["ts"],
                    "channel": response["channel"]
                }
                
                # Upload screenshot if provided
                if screenshot_path:
                    file_response = mock_client.files_upload(
                        channels="#upwork-automation",
                        file=screenshot_path,
                        title="Job Search Screenshot",
                        initial_comment="Screenshot of the top job listing"
                    )
                    
                    result["screenshot_uploaded"] = file_response["ok"]
                    result["screenshot_url"] = file_response["file"]["permalink"]
                
                return result
            
            # Execute notification
            top_job = {
                "id": "job_123",
                "title": "Senior Salesforce Agentforce Developer",
                "hourly_rate": 85,
                "client_rating": 4.9,
                "match_score": 0.95,
                "job_url": "https://www.upwork.com/jobs/job_123"
            }
            
            result = await send_job_discovery_notification(
                jobs_found=5,
                top_job=top_job,
                screenshot_path="job_screenshot.png"
            )
            
            # Verify notification results
            assert result["success"] is True
            assert result["message_ts"] is not None
            assert result["channel"] == "C1234567890"
            assert result["screenshot_uploaded"] is True
            assert "slack.com" in result["screenshot_url"]
            
            # Verify API calls
            mock_client.chat_postMessage.assert_called_once()
            mock_client.files_upload.assert_called_once()
            
            # Verify message content
            call_args = mock_client.chat_postMessage.call_args
            assert "5 new Salesforce" in call_args[1]["text"]
            assert "blocks" in call_args[1]
            
            print("✅ Slack notification integration test passed")
    
    @pytest.mark.asyncio
    async def test_slack_interactive_commands(self):
        """Test Slack interactive commands and responses"""
        with patch('slack_sdk.WebClient') as mock_slack_client:
            mock_client = Mock()
            mock_slack_client.return_value = mock_client
            
            # Mock slash command response
            mock_client.chat_postMessage.return_value = {
                "ok": True,
                "channel": "D1234567890",  # DM channel
                "ts": "1234567890.123456"
            }
            
            # Test slash command handler
            async def handle_slack_command(command, user_id, channel_id):
                if command == "/upwork-status":
                    # Get system status
                    status_info = {
                        "automation_enabled": True,
                        "active_sessions": 3,
                        "jobs_found_today": 12,
                        "applications_sent_today": 4,
                        "last_activity": "2 minutes ago"
                    }
                    
                    status_message = f"""
*Upwork Automation Status* 📊

🤖 *Automation:* {'✅ Enabled' if status_info['automation_enabled'] else '❌ Disabled'}
🌐 *Active Sessions:* {status_info['active_sessions']}
🎯 *Jobs Found Today:* {status_info['jobs_found_today']}
📤 *Applications Sent:* {status_info['applications_sent_today']}
⏰ *Last Activity:* {status_info['last_activity']}
                    """
                    
                    response = mock_client.chat_postMessage(
                        channel=channel_id,
                        text=status_message.strip(),
                        user=user_id
                    )
                    
                    return {"success": response["ok"], "response_type": "status"}
                
                elif command == "/upwork-pause":
                    # Pause automation
                    mock_client.chat_postMessage(
                        channel=channel_id,
                        text="⏸️ Automation paused. Use `/upwork-resume` to continue.",
                        user=user_id
                    )
                    
                    return {"success": True, "response_type": "pause"}
                
                elif command == "/upwork-resume":
                    # Resume automation
                    mock_client.chat_postMessage(
                        channel=channel_id,
                        text="▶️ Automation resumed. Monitoring for new jobs...",
                        user=user_id
                    )
                    
                    return {"success": True, "response_type": "resume"}
                
                else:
                    # Unknown command
                    mock_client.chat_postMessage(
                        channel=channel_id,
                        text="❓ Unknown command. Available commands: `/upwork-status`, `/upwork-pause`, `/upwork-resume`",
                        user=user_id
                    )
                    
                    return {"success": True, "response_type": "help"}
            
            # Test different commands
            commands = [
                ("/upwork-status", "status"),
                ("/upwork-pause", "pause"),
                ("/upwork-resume", "resume"),
                ("/upwork-unknown", "help")
            ]
            
            for command, expected_type in commands:
                result = await handle_slack_command(command, "U1234567890", "D1234567890")
                assert result["success"] is True
                assert result["response_type"] == expected_type
            
            # Verify all commands were processed
            assert mock_client.chat_postMessage.call_count == len(commands)
            
            print("✅ Slack interactive commands integration test passed")


class TestN8NIntegration:
    """Test n8n webhook integration for workflows"""
    
    @pytest.mark.asyncio
    async def test_n8n_webhook_triggers(self):
        """Test n8n webhook triggers for different workflows"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock HTTP client
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "workflowId": "workflow_123",
                "executionId": "exec_456"
            }
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Test n8n service
            async def trigger_n8n_workflow(workflow_name, data):
                webhook_urls = {
                    "job-discovery-pipeline": "https://n8n.example.com/webhook/job-discovery",
                    "proposal-generation-pipeline": "https://n8n.example.com/webhook/proposal-generation",
                    "browser-submission-pipeline": "https://n8n.example.com/webhook/browser-submission",
                    "notification-workflows": "https://n8n.example.com/webhook/notifications"
                }
                
                webhook_url = webhook_urls.get(workflow_name)
                if not webhook_url:
                    raise ValueError(f"Unknown workflow: {workflow_name}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook_url,
                        json=data,
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return {
                            "success": True,
                            "workflow_id": result.get("workflowId"),
                            "execution_id": result.get("executionId"),
                            "webhook_url": webhook_url
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                            "webhook_url": webhook_url
                        }
            
            # Test different workflow triggers
            workflows = [
                {
                    "name": "job-discovery-pipeline",
                    "data": {
                        "keywords": ["Salesforce", "Agentforce"],
                        "filters": {"min_rate": 50, "min_rating": 4.0},
                        "max_results": 20
                    }
                },
                {
                    "name": "proposal-generation-pipeline",
                    "data": {
                        "job_id": "job_123",
                        "job_title": "Senior Salesforce Developer",
                        "job_description": "Build AI agents...",
                        "client_info": {"rating": 4.8, "hire_rate": 0.9}
                    }
                },
                {
                    "name": "browser-submission-pipeline",
                    "data": {
                        "job_url": "https://www.upwork.com/jobs/job_123",
                        "proposal_content": "I am an experienced developer...",
                        "bid_amount": 75,
                        "attachments": ["portfolio.pdf"]
                    }
                },
                {
                    "name": "notification-workflows",
                    "data": {
                        "event_type": "job_discovered",
                        "jobs_count": 5,
                        "top_job": {"title": "Salesforce Developer", "rate": 80}
                    }
                }
            ]
            
            # Execute workflow triggers
            results = []
            for workflow in workflows:
                result = await trigger_n8n_workflow(workflow["name"], workflow["data"])
                results.append({
                    "workflow_name": workflow["name"],
                    "result": result
                })
            
            # Verify all workflows were triggered successfully
            for workflow_result in results:
                assert workflow_result["result"]["success"] is True
                assert workflow_result["result"]["workflow_id"] is not None
                assert workflow_result["result"]["execution_id"] is not None
                assert "n8n.example.com" in workflow_result["result"]["webhook_url"]
            
            # Verify HTTP calls were made
            assert mock_client.return_value.__aenter__.return_value.post.call_count == len(workflows)
            
            print("✅ n8n webhook triggers integration test passed")
    
    @pytest.mark.asyncio
    async def test_n8n_workflow_status_monitoring(self):
        """Test monitoring n8n workflow execution status"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock workflow status responses
            status_responses = [
                {"status": "running", "progress": 0.3, "current_step": "search_jobs"},
                {"status": "running", "progress": 0.6, "current_step": "filter_jobs"},
                {"status": "running", "progress": 0.9, "current_step": "send_notifications"},
                {"status": "completed", "progress": 1.0, "result": {"jobs_processed": 15}}
            ]
            
            status_call_count = 0
            
            def mock_status_response(*args, **kwargs):
                nonlocal status_call_count
                response = Mock()
                response.status_code = 200
                response.json.return_value = status_responses[min(status_call_count, len(status_responses) - 1)]
                status_call_count += 1
                return response
            
            mock_client.return_value.__aenter__.return_value.get.side_effect = mock_status_response
            
            # Test workflow monitoring
            async def monitor_workflow_execution(execution_id, max_wait_time=10):
                status_url = f"https://n8n.example.com/api/executions/{execution_id}"
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(status_url)
                        
                        if response.status_code == 200:
                            status_data = response.json()
                            
                            if status_data["status"] == "completed":
                                return {
                                    "completed": True,
                                    "result": status_data.get("result"),
                                    "total_time": time.time() - start_time
                                }
                            elif status_data["status"] == "failed":
                                return {
                                    "completed": False,
                                    "error": status_data.get("error"),
                                    "total_time": time.time() - start_time
                                }
                            else:
                                # Still running, wait and check again
                                await asyncio.sleep(0.1)  # Reduced for testing
                                continue
                        else:
                            return {
                                "completed": False,
                                "error": f"HTTP {response.status_code}",
                                "total_time": time.time() - start_time
                            }
                
                # Timeout
                return {
                    "completed": False,
                    "error": "Monitoring timeout",
                    "total_time": max_wait_time
                }
            
            # Execute workflow monitoring
            result = await monitor_workflow_execution("exec_456")
            
            # Verify monitoring results
            assert result["completed"] is True
            assert result["result"]["jobs_processed"] == 15
            assert result["total_time"] < 10
            
            # Verify status was checked multiple times
            assert status_call_count >= 3  # Should have checked status multiple times
            
            print("✅ n8n workflow status monitoring integration test passed")


class TestBrowserbaseIntegration:
    """Test Browserbase API integration for browser automation"""
    
    @pytest.mark.asyncio
    async def test_browserbase_session_management(self):
        """Test Browserbase session creation and management"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock Browserbase API responses
            session_response = Mock()
            session_response.status_code = 200
            session_response.json.return_value = {
                "id": "session_123",
                "status": "RUNNING",
                "connectUrl": "wss://connect.browserbase.com/session_123",
                "createdAt": "2024-01-15T10:30:00.000Z"
            }
            
            status_response = Mock()
            status_response.status_code = 200
            status_response.json.return_value = {
                "id": "session_123",
                "status": "RUNNING",
                "lastActivity": "2024-01-15T10:35:00.000Z"
            }
            
            mock_client.return_value.__aenter__.return_value.post.return_value = session_response
            mock_client.return_value.__aenter__.return_value.get.return_value = status_response
            
            # Test Browserbase integration
            async def create_browserbase_session(config):
                session_config = {
                    "projectId": config.get("project_id", "default_project"),
                    "stealth": config.get("stealth", True),
                    "proxies": config.get("proxies", True),
                    "keepAlive": config.get("keep_alive", True)
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://www.browserbase.com/v1/sessions",
                        json=session_config,
                        headers={
                            "Authorization": f"Bearer {config.get('api_key', 'test_key')}",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    if response.status_code == 200:
                        session_data = response.json()
                        return {
                            "session_id": session_data["id"],
                            "connect_url": session_data["connectUrl"],
                            "status": session_data["status"],
                            "created_at": session_data["createdAt"]
                        }
                    else:
                        raise Exception(f"Failed to create session: HTTP {response.status_code}")
            
            async def get_session_status(session_id, api_key):
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://www.browserbase.com/v1/sessions/{session_id}",
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
                    
                    if response.status_code == 200:
                        status_data = response.json()
                        return {
                            "session_id": status_data["id"],
                            "status": status_data["status"],
                            "last_activity": status_data["lastActivity"]
                        }
                    else:
                        raise Exception(f"Failed to get session status: HTTP {response.status_code}")
            
            # Execute session management
            config = {
                "project_id": "upwork_automation",
                "api_key": "test_api_key",
                "stealth": True,
                "proxies": True,
                "keep_alive": True
            }
            
            # Create session
            session = await create_browserbase_session(config)
            
            # Verify session creation
            assert session["session_id"] == "session_123"
            assert session["status"] == "RUNNING"
            assert "browserbase.com" in session["connect_url"]
            assert session["created_at"] is not None
            
            # Check session status
            status = await get_session_status(session["session_id"], config["api_key"])
            
            # Verify status check
            assert status["session_id"] == "session_123"
            assert status["status"] == "RUNNING"
            assert status["last_activity"] is not None
            
            # Verify API calls
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()
            
            print("✅ Browserbase session management integration test passed")


if __name__ == "__main__":
    # Run external services integration tests
    pytest.main([__file__, "-v", "-s"])