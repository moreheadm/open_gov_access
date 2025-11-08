"""
MCP Server for Mission Local Civic Data Platform
Exposes civic data to AI assistants via Model Context Protocol
"""

import json
import asyncio
from pathlib import Path
from typing import Any, Sequence
from datetime import datetime

# MCP Server implementation
# Install: pip install mcp --break-system-packages

from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import mcp.server.stdio


class CivicDataMCPServer:
    """MCP Server for civic data access"""
    
    def __init__(self, data_dir: str = "data/sfbos_meetings_demo"):
        self.data_dir = Path(data_dir)
        self.text_dir = self.data_dir / "text"
        self.metadata_dir = self.data_dir / "metadata"
        self.server = Server("civic-data-mcp")
        
        # Register handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up MCP protocol handlers"""
        
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List all available civic documents as resources"""
            resources = []
            
            if self.metadata_dir.exists():
                for meta_file in self.metadata_dir.glob("*.json"):
                    with open(meta_file) as f:
                        metadata = json.load(f)
                    
                    resources.append(Resource(
                        uri=f"civic://document/{meta_file.stem}",
                        name=f"{metadata['doc_type'].title()}: {metadata['meeting_date']}",
                        description=f"Board of Supervisors {metadata['doc_type']} from {metadata['meeting_date']}",
                        mimeType="text/plain"
                    ))
            
            return resources
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a specific civic document"""
            # Parse URI: civic://document/{filename}
            if not uri.startswith("civic://document/"):
                raise ValueError(f"Invalid URI: {uri}")
            
            filename = uri.replace("civic://document/", "")
            text_file = self.text_dir / f"{filename}.txt"
            
            if not text_file.exists():
                raise FileNotFoundError(f"Document not found: {filename}")
            
            return text_file.read_text()
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools for querying civic data"""
            return [
                Tool(
                    name="search_documents",
                    description="Search through civic documents by keyword, date, or document type",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (keywords to find in documents)"
                            },
                            "doc_type": {
                                "type": "string",
                                "enum": ["agenda", "minutes", "all"],
                                "description": "Type of document to search"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date filter (YYYY-MM-DD format)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date filter (YYYY-MM-DD format)"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_document_by_date",
                    description="Retrieve board meeting documents for a specific date",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Meeting date (e.g., 'October 21, 2025' or '2025-10-21')"
                            },
                            "doc_type": {
                                "type": "string",
                                "enum": ["agenda", "minutes", "both"],
                                "default": "both",
                                "description": "Which document to retrieve"
                            }
                        },
                        "required": ["date"]
                    }
                ),
                Tool(
                    name="find_by_address",
                    description="Find all board documents mentioning a specific address",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "address": {
                                "type": "string",
                                "description": "Address to search for (e.g., '1234 Mission Street')"
                            }
                        },
                        "required": ["address"]
                    }
                ),
                Tool(
                    name="find_by_file_number",
                    description="Find board documents related to a specific file number",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_number": {
                                "type": "string",
                                "description": "File number to search for (e.g., '250210')"
                            }
                        },
                        "required": ["file_number"]
                    }
                ),
                Tool(
                    name="list_recent_meetings",
                    description="List the most recent board meetings with available documents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "default": 10,
                                "description": "Number of meetings to return"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
            """Execute a tool"""
            
            if name == "search_documents":
                results = self._search_documents(
                    query=arguments["query"],
                    doc_type=arguments.get("doc_type", "all"),
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date")
                )
                return [TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )]
            
            elif name == "get_document_by_date":
                results = self._get_document_by_date(
                    date=arguments["date"],
                    doc_type=arguments.get("doc_type", "both")
                )
                return [TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )]
            
            elif name == "find_by_address":
                results = self._find_by_address(arguments["address"])
                return [TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )]
            
            elif name == "find_by_file_number":
                results = self._find_by_file_number(arguments["file_number"])
                return [TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )]
            
            elif name == "list_recent_meetings":
                results = self._list_recent_meetings(arguments.get("limit", 10))
                return [TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )]
            
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    def _search_documents(self, query: str, doc_type: str, start_date: str | None, end_date: str | None) -> dict:
        """Search through documents"""
        results = []
        query_lower = query.lower()
        
        for text_file in self.text_dir.glob("*.txt"):
            # Check doc type filter
            if doc_type != "all" and doc_type not in text_file.name:
                continue
            
            # Read metadata
            meta_file = self.metadata_dir / f"{text_file.stem}.json"
            if meta_file.exists():
                with open(meta_file) as f:
                    metadata = json.load(f)
            else:
                continue
            
            # Check date filters (simplified)
            # TODO: Proper date parsing
            
            # Search in content
            content = text_file.read_text()
            if query_lower in content.lower():
                # Find context around matches
                lines = content.split('\n')
                matching_snippets = []
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        snippet = '\n'.join(lines[start:end])
                        matching_snippets.append(snippet)
                
                results.append({
                    "document": text_file.name,
                    "meeting_date": metadata["meeting_date"],
                    "doc_type": metadata["doc_type"],
                    "url": metadata["url"],
                    "matches": len(matching_snippets),
                    "snippets": matching_snippets[:3]  # First 3 matches
                })
        
        return {
            "query": query,
            "total_results": len(results),
            "results": results
        }
    
    def _get_document_by_date(self, date: str, doc_type: str) -> dict:
        """Get documents for a specific date"""
        results = []
        
        # Normalize date format
        # This is simplified - you'd want better date parsing
        date_variations = [
            date,
            date.replace("-", " "),
            date.replace(" ", "-")
        ]
        
        for text_file in self.text_dir.glob("*.txt"):
            # Check if any date variation is in filename
            if any(d.replace(",", "") in text_file.name for d in date_variations):
                if doc_type == "both" or doc_type in text_file.name:
                    content = text_file.read_text()
                    meta_file = self.metadata_dir / f"{text_file.stem}.json"
                    
                    metadata = {}
                    if meta_file.exists():
                        with open(meta_file) as f:
                            metadata = json.load(f)
                    
                    results.append({
                        "document": text_file.name,
                        "doc_type": metadata.get("doc_type", "unknown"),
                        "content": content,
                        "url": metadata.get("url", "")
                    })
        
        return {
            "date": date,
            "documents_found": len(results),
            "documents": results
        }
    
    def _find_by_address(self, address: str) -> dict:
        """Find documents mentioning an address"""
        return self._search_documents(address, "all", None, None)
    
    def _find_by_file_number(self, file_number: str) -> dict:
        """Find documents mentioning a file number"""
        return self._search_documents(file_number, "all", None, None)
    
    def _list_recent_meetings(self, limit: int) -> dict:
        """List recent meetings"""
        meetings = []
        
        # Group by meeting date
        meeting_dates = {}
        for meta_file in sorted(self.metadata_dir.glob("*.json"), reverse=True):
            with open(meta_file) as f:
                metadata = json.load(f)
            
            date = metadata["meeting_date"]
            if date not in meeting_dates:
                meeting_dates[date] = {
                    "date": date,
                    "documents": []
                }
            
            meeting_dates[date]["documents"].append({
                "type": metadata["doc_type"],
                "url": metadata["url"],
                "file": meta_file.stem
            })
        
        meetings = list(meeting_dates.values())[:limit]
        
        return {
            "total_meetings": len(meetings),
            "meetings": meetings
        }
    
    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point"""
    server = CivicDataMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
