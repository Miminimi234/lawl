"""
AI-Powered Legal Analysis Service
Uses OpenAI GPT-4 to generate comprehensive legal opinions
"""
import os
from typing import Dict, List, Optional
import openai
from openai import OpenAI

class AILegalAnalyzer:
    """Generate comprehensive legal analysis using OpenAI GPT-4"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        # Initialize OpenAI client with minimal config
        try:
            self.client = OpenAI(api_key=self.api_key)
        except TypeError as e:
            # Fallback for older OpenAI versions
            import openai as openai_module
            openai_module.api_key = self.api_key
            self.client = openai_module
        
    def generate_legal_analysis(
        self,
        case_title: str,
        case_type: str,
        facts: str,
        jurisdiction: str,
        amount: Optional[int] = None
    ) -> Dict:
        """
        Generate comprehensive legal analysis for a case
        
        Returns dict with:
        - judge_analyses: List of 3 detailed judicial opinions
        - consensus: Panel consensus opinion
        - recommendation: Final verdict
        - confidence: Confidence score
        """
        
        # Generate analysis from each judge's perspective
        judge_analyses = []
        
        # Judge 1: Contract/Commercial Law Expert
        judge_1 = self._generate_judge_opinion(
            judge_name="Judge Elena Martinez",
            specialty="Contract & Commercial Law",
            case_title=case_title,
            case_type=case_type,
            facts=facts,
            jurisdiction=jurisdiction,
            amount=amount,
            perspective="Focus on contract formation, breach analysis, damages calculation, and UCC principles. Apply Restatement (Second) of Contracts frameworks. Cite landmark contract law cases."
        )
        judge_analyses.append(judge_1)
        
        # Judge 2: Procedure/Evidence Expert
        judge_2 = self._generate_judge_opinion(
            judge_name="Judge David Chen",
            specialty="Civil Procedure & Evidence",
            case_title=case_title,
            case_type=case_type,
            facts=facts,
            jurisdiction=jurisdiction,
            amount=amount,
            perspective="Focus on burden-shifting, evidentiary standards, procedural requirements, and causation analysis. Apply Federal Rules of Evidence and Civil Procedure."
        )
        judge_analyses.append(judge_2)
        
        # Judge 3: Constitutional/Statutory Expert
        judge_3 = self._generate_judge_opinion(
            judge_name="Judge Sarah Williams",
            specialty="Constitutional & Statutory Interpretation",
            case_title=case_title,
            case_type=case_type,
            facts=facts,
            jurisdiction=jurisdiction,
            amount=amount,
            perspective="Focus on statutory interpretation, constitutional analysis, legislative intent, and policy considerations. Apply canons of construction and constitutional frameworks."
        )
        judge_analyses.append(judge_3)
        
        # Generate consensus opinion
        consensus = self._generate_consensus(
            case_title=case_title,
            case_type=case_type,
            facts=facts,
            judge_analyses=judge_analyses,
            amount=amount
        )
        
        return {
            "judge_analyses": judge_analyses,
            "consensus": consensus,
            "recommendation": consensus["final_verdict"],
            "confidence": consensus["confidence"]
        }
    
    def _generate_judge_opinion(
        self,
        judge_name: str,
        specialty: str,
        case_title: str,
        case_type: str,
        facts: str,
        jurisdiction: str,
        amount: Optional[int],
        perspective: str
    ) -> Dict:
        """Generate a single judge's detailed opinion"""
        
        system_prompt = f"""You are {judge_name}, a distinguished federal appellate judge specializing in {specialty}. 

You write comprehensive, rigorous legal opinions that:
- Apply appropriate legal frameworks and tests
- Cite relevant case precedents (real cases)
- Analyze element-by-element
- Consider and reject defenses
- Provide detailed reasoning
- Calculate specific damages when applicable
- Use proper legal citation format

Write in a formal judicial opinion style with numbered sections and subsections."""

        user_prompt = f"""Analyze this {case_type} case and write a comprehensive judicial opinion from your perspective as a {specialty} expert.

CASE: {case_title}
JURISDICTION: {jurisdiction}
CASE TYPE: {case_type}

FACTS:
{facts}

{f'DAMAGES SOUGHT: ${amount:,}' if amount else ''}

YOUR ANALYTICAL PERSPECTIVE:
{perspective}

REQUIRED STRUCTURE:
I. APPLICABLE LEGAL FRAMEWORK - Identify controlling law and tests
II. ELEMENT-BY-ELEMENT ANALYSIS - Apply law to facts systematically
III. PRECEDENTIAL AUTHORITY - Cite and distinguish relevant cases
IV. DEFENSES CONSIDERED - Address and resolve counterarguments
V. DAMAGES/REMEDIES - Calculate and justify relief (if applicable)
VI. CONCLUSION - Final recommendation with reasoning

Be comprehensive (aim for 800-1200 words). Use specific legal tests, cite real cases, and provide detailed analysis. This should read like an actual federal court opinion."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            reasoning = response.choices[0].message.content.strip()
            
            # Extract recommendation (last paragraph usually contains it)
            lines = reasoning.split('\n')
            recommendation = next(
                (line for line in reversed(lines) if 'recommend' in line.lower() or 'judgment' in line.lower()),
                "Judgment for plaintiff"
            )
            
            # Determine confidence based on strength of analysis
            confidence_prompt = f"Based on this legal analysis, rate the confidence level (0.0-1.0) that this is the correct legal outcome:\n\n{reasoning}\n\nProvide only a decimal number between 0.75 and 0.98."
            
            confidence_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": confidence_prompt}],
                temperature=0.3,
                max_tokens=10
            )
            
            try:
                confidence = float(confidence_response.choices[0].message.content.strip())
                confidence = max(0.75, min(0.98, confidence))  # Clamp to reasonable range
            except:
                confidence = 0.88  # Default
            
            # Determine framework used
            framework_map = {
                'contract': 'contract_formation_breach_damages',
                'employment': 'mcdonnell_douglas_burden_shifting',
                'civil_rights': 'section_1983_qualified_immunity',
                'property': 'property_rights_enforcement',
                'criminal': 'reasonable_doubt_burden_of_proof'
            }
            framework = framework_map.get(case_type, 'general_legal_analysis')
            
            return {
                "judge_name": judge_name,
                "specialty": specialty,
                "framework_used": framework,
                "reasoning": reasoning,
                "recommendation": recommendation,
                "confidence": round(confidence, 2)
            }
            
        except Exception as e:
            print(f"Error generating judge opinion: {e}")
            # Fallback to basic response
            return {
                "judge_name": judge_name,
                "specialty": specialty,
                "framework_used": "general_analysis",
                "reasoning": f"[AI Analysis Error: {str(e)}] This case requires careful analysis of the facts presented.",
                "recommendation": "Further analysis required",
                "confidence": 0.70
            }
    
    def _generate_consensus(
        self,
        case_title: str,
        case_type: str,
        facts: str,
        judge_analyses: List[Dict],
        amount: Optional[int]
    ) -> Dict:
        """Generate panel consensus based on individual opinions"""
        
        # Combine all judge reasoning
        all_reasoning = "\n\n---\n\n".join([
            f"**{j['judge_name']} ({j['specialty']}):**\n{j['reasoning']}"
            for j in judge_analyses
        ])
        
        consensus_prompt = f"""You are writing the PANEL CONSENSUS opinion for a three-judge appellate panel.

CASE: {case_title}
CASE TYPE: {case_type}

INDIVIDUAL JUDGE OPINIONS:
{all_reasoning}

Write a concise consensus opinion (300-400 words) that:
1. Summarizes the unanimous or majority holding
2. Synthesizes the key reasoning from all three judges
3. States the final verdict clearly
4. Explains why this outcome is legally correct
5. Lists the legal frameworks applied

Use formal judicial language. Begin with "The Panel unanimously finds..." or "The Panel holds..."
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": consensus_prompt}],
                temperature=0.6,
                max_tokens=800
            )
            
            consensus_reasoning = response.choices[0].message.content.strip()
            
            # Extract verdict
            verdict_prompt = f"Based on this consensus opinion, provide a one-sentence final verdict (e.g., 'Judgment for Plaintiff. Award $X in damages.'):\n\n{consensus_reasoning}"
            
            verdict_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": verdict_prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            final_verdict = verdict_response.choices[0].message.content.strip()
            
            # Calculate consensus confidence (average of all judges)
            avg_confidence = sum(j['confidence'] for j in judge_analyses) / len(judge_analyses)
            
            # Agreement score (all judges agree = 3, majority = 2)
            agreement_score = 3  # Assume unanimous for now
            
            # Framework consensus
            frameworks = [j['framework_used'] for j in judge_analyses]
            framework_consensus = f"Applied frameworks: {', '.join(set(frameworks))}"
            
            return {
                "final_verdict": final_verdict,
                "agreement_score": agreement_score,
                "reasoning": consensus_reasoning,
                "framework_consensus": framework_consensus,
                "confidence": round(avg_confidence, 2)
            }
            
        except Exception as e:
            print(f"Error generating consensus: {e}")
            return {
                "final_verdict": "Judgment pending further review",
                "agreement_score": 3,
                "reasoning": f"[AI Consensus Error: {str(e)}] The panel is reviewing all arguments.",
                "framework_consensus": "Standard legal analysis",
                "confidence": 0.75
            }







