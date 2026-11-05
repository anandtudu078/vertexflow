from pydantic import BaseModel
from typing import List

from backend.agents.llm import generate_structured


class VulnerabilityItem(BaseModel):
    vulnerability_id: str
    severity: str  # e.g., "Critical", "Warning", "Info"
    description: str
    remediation: str


class SecurityAuditReport(BaseModel):
    security_score: int  # Scale of 1 to 100
    overall_status: str  # e.g., "Passed", "Requires Fixes", "Rejected"
    vulnerabilities: List[VulnerabilityItem]
    compliance_notes: str


def run_security_auditor_agent(project_statement: str, backend_code: str, frontend_code: str) -> SecurityAuditReport:
    """
    The Security Auditor Agent reviews generated code for vulnerabilities,
    secrets leakage, missing auth checks, and security compliance.
    """
    prompt = f"""
    You are the Chief Information Security Officer (CISO) and Security Auditor Agent of VertexFlow.

    Project Statement: "{project_statement}"

    Generated Backend Code / Blueprint:
    {backend_code}

    Generated Frontend Code / Blueprint:
    {frontend_code}

    Your job is to audit this code for security flaws. Analyze for:
    1. Hardcoded API keys, tokens, or credentials.
    2. Missing input validation or authentication protection on endpoints.
    3. Common web vulnerabilities (e.g., injection, insecure state management).

    Provide a security score (1-100), overall status, a list of identified vulnerabilities with severity levels, and specific remediation advice.
    """

    return SecurityAuditReport.model_validate_json(
        generate_structured(prompt, SecurityAuditReport, "security_auditor")
    )