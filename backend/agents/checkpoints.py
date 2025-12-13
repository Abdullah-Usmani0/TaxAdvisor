"""Checkpoint management and utilities"""
from typing import List, Dict, Any
from backend.models import ResearchSource
import re


def parse_research_sources(research_context: str) -> List[ResearchSource]:
    """
    Parse research context string into structured ResearchSource objects
    
    Args:
        research_context: Raw research context from Tavily searches
    
    Returns:
        List of ResearchSource objects
    """
    sources = []
    
    # Split by query sections
    sections = research_context.split("### Query:")
    
    for section in sections[1:]:  # Skip first empty section
        # Extract sources from this query section
        lines = section.strip().split("\n")
        
        current_url = ""
        current_content = ""
        index = len(sources)
        
        for line in lines:
            if line.startswith("- Source:"):
                # Save previous source if exists
                if current_url:
                    sources.append(ResearchSource(
                        index=index,
                        url=current_url,
                        title=extract_domain(current_url),
                        snippet=current_content.strip(),
                        relevance_score=None
                    ))
                    index += 1
                
                # Start new source
                current_url = line.replace("- Source:", "").strip()
                current_content = ""
            
            elif line.startswith("  Content:"):
                current_content = line.replace("  Content:", "").strip()
        
        # Add last source
        if current_url:
            sources.append(ResearchSource(
                index=index,
                url=current_url,
                title=extract_domain(current_url),
                snippet=current_content.strip()
            ))
    
    return sources


def extract_domain(url: str) -> str:
    """Extract domain name from URL for display as title"""
    try:
        # Simple domain extraction
        domain = url.split("//")[-1].split("/")[0]
        # Remove www prefix
        domain = domain.replace("www.", "")
        return domain.capitalize()
    except:
        return "Unknown Source"


def filter_research_by_approved_sources(
    research_context: str,
    approved_indices: List[int]
) -> str:
    """
    Filter research context to only include approved sources
    
    Args:
        research_context: Original research context
        approved_indices: List of approved source indices
    
    Returns:
        Filtered research context
    """
    if not approved_indices:
        return research_context
    
    sources = parse_research_sources(research_context)
    approved_sources = [s for s in sources if s.index in approved_indices]
    
    # Reconstruct context with only approved sources
    filtered_context = []
    for source in approved_sources:
        filtered_context.append(
            f"- Source: {source.url}\n  Content: {source.snippet}"
        )
    
    return "\n\n".join(filtered_context)


def get_checkpoint_state_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of checkpoint state for API response
    
    Args:
        state: Current workflow state
    
    Returns:
        Summary dict with key information
    """
    profile = state.get("profile", {})
    research_plan = state.get("research_plan", {})
    
    return {
        "client_name": profile.get("client_name", "Unknown"),
        "tax_scenario": f"{profile.get('tax_residency_current', '')} → {profile.get('tax_residency_target', '')}",
        "research_queries": research_plan.get("queries", []),
        "research_rationale": research_plan.get("rationale", ""),
        "total_sources": len(parse_research_sources(state.get("research_context", "")))
    }

