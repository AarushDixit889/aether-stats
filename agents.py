# agents.py
import os
from pydantic import BaseModel, Field, conlist
from typing import List, Optional, Dict, Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# --- API Key Handling ---
API_KEY = os.getenv("STATS_API_KEY") or os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise ValueError(
        "API key not found. Please set STATS_API_KEY or OPENROUTER_API_KEY environment variable."
    )

# Ensure OpenRouter API key is set in the environment for pydantic-ai
os.environ['OPENROUTER_API_KEY'] = API_KEY

# --- Initialize the AI Model ---
# Using the specified model with OpenRouter provider
model = OpenAIModel(
    "mistralai/devstral-small-2505:free",
    provider="openrouter"
)

# --- Agent Output Models ---

# 1. Register File AutoDescribe Output Model (Enhanced)
class RegisterFileAutoDescribeOutput(BaseModel):
    """
    Structured report for automatically describing a registered data file.
    """
    overview: str = Field(description="A concise summary and high-level understanding of the data file's content.")
    key_variables: List[Dict[str, str]] = Field(
        description="A list of dictionaries, each describing a key variable (column) with its name and a brief explanation of its meaning or type (e.g., {'name': 'age', 'description': 'Numerical, represents customer age in years.'})."
    )
    observations: List[str] = Field(
        description="Key observations, patterns, or immediate insights from the data (e.g., 'Appears to be time-series data', 'Contains both numerical and categorical features')."
    )
    potential_issues: List[str] = Field(
        description="Any potential data quality issues, anomalies, or concerns identified (e.g., 'Missing values in 'income' column', 'Outliers detected in 'price'')."
    )
    suggested_next_steps: List[str] = Field(
        description="Recommendations for immediate next steps for a statistician or data analyst (e.g., 'Perform data cleaning and imputation', 'Visualize correlations between numerical features')."
    )

# 2. AetherExplain Output Model
class AetherExplainOutput(BaseModel):
    """
    Structured explanation for statistical analysis results.
    """
    explanation: str = Field(
        description="A clear, concise explanation of the statistical results in natural language, avoiding jargon where possible."
    )
    statistical_significance: Optional[str] = Field(
        description="An interpretation of the statistical significance (e.g., 'The difference observed is statistically significant, meaning it's unlikely due to chance.')."
    )
    implications: str = Field(
        description="What the results mean in the context of the original question or business problem."
    )
    limitations: Optional[str] = Field(
        description="Any important limitations or assumptions of the analysis that users should be aware of."
    )
    suggested_follow_up: List[str] = Field(
        description="Recommendations for further analysis or visualizations based on these results."
    )

# 3. AetherInsight Output Model
class AetherInsightOutput(BaseModel):
    """
    Structured insights and anomaly detection from a data summary.
    """
    insights: List[str] = Field(
        description="A list of key patterns, trends, or interesting findings identified in the data."
    )
    anomalies: List[str] = Field(
        description="A list of unusual data points, clusters, or behaviors that warrant further investigation."
    )
    key_relationships: List[Dict[str, str]] = Field(
        description="A list of significant relationships or correlations found between variables (e.g., {'variables': 'age_income', 'description': 'Strong positive correlation observed between age and income.'})."
    )
    actionable_recommendations: List[str] = Field(
        description="Practical recommendations derived from the insights, suggesting concrete actions or areas for focus."
    )

# 4. AetherHypothesize Output Model
class AetherHypothesizeOutput(BaseModel):
    """
    Structured list of statistical hypotheses generated from data characteristics.
    """
    hypotheses: List[Dict[str, str]] = Field(
        description="A list of dictionaries, each representing a testable statistical hypothesis. Each dictionary should have 'hypothesis' (the statement), 'suggested_test' (e.g., 'T-test', 'ANOVA', 'Chi-square'), and 'reasoning' (why this hypothesis and test are relevant given the data)."
    )
    potential_challenges: List[str] = Field(
        description="Potential issues or prerequisites for testing these hypotheses (e.g., 'Requires sufficient sample size', 'Assumes normality of data')."
    )

# 5. AetherCommandSuggest Output Model
class AetherCommandSuggestOutput(BaseModel):
    """
    Structured suggestions for AetherStats CLI commands based on natural language input.
    """
    suggested_commands: conlist(str, min_length=1) = Field( # Ensures at least one command
        description="A list of AetherStats CLI commands that can achieve the user's intent."
    )
    explanation: str = Field(
        description="A brief explanation of why these commands are suggested and what they will accomplish."
    )
    clarification_needed: Optional[str] = Field(
        description="If the query is ambiguous, a question to ask the user for clarification."
    )

# --- NEW Output Models for New Features ---

class AnalysisResult(BaseModel):
    """Represents the result of a single statistical analysis or test."""
    test_name: str = Field(description="Name of the statistical test performed (e.g., 'Independent T-Test', 'Pearson Correlation', 'Linear Regression').")
    summary: str = Field(description="A concise summary of the test's findings.")
    p_value: Optional[float] = Field(None, description="The p-value of the test, if applicable.")
    interpretation: str = Field(description="A natural language interpretation of the results, including significance.")
    key_metrics: Dict[str, Any] = Field(default_factory=dict, description="Key numerical metrics from the analysis (e.g., t-statistic, R-squared, coefficients).")
    assumptions_notes: Optional[str] = Field(None, description="Notes on assumptions and whether they seem to be met or violated.")

class AnalysisOutput(BaseModel):
    """Comprehensive output for the 'analyze' command."""
    analyses: List[AnalysisResult] = Field(description="A list of analysis results performed.")
    overall_conclusion: str = Field(description="An overall conclusion based on all performed analyses.")
    suggested_follow_up: List[str] = Field(default_factory=list, description="Suggested next steps after this analysis.")

class CodeGenerationOutput(BaseModel):
    """Structured output for generated code."""
    code: str = Field(description="The generated Python code as a string.")
    explanation: str = Field(description="An explanation of what the code does and how to use it.")
    required_packages: List[str] = Field(default_factory=list, description="List of Python packages required to run this code.")
    filename_suggestion: str = Field(description="Suggested filename for the generated script (e.g., 'data_cleaning.py').")

class MarkdownReportOutput(BaseModel):
    """Structured output for a Markdown report."""
    markdown_content: str = Field(description="The complete Markdown content for the report.")
    title: str = Field(description="Suggested title for the report.")
    summary: str = Field(description="A brief summary of the report's main points.")


# --- Define AetherStats Agents ---

# Existing Agents (re-defined with correct Agent class)
register_file_auto_describe_agent = Agent(
    model,
    output_type=RegisterFileAutoDescribeOutput,
    instructions=(
        "Analyze the provided data summary and generate a structured report describing its content, "
        "key variables, observations, potential issues, and suggested next steps for a statistician. "
        "Focus on statistical relevance and data quality."
    ),
    system_prompt=(
        "You are an expert statistician with decades of experience in data analysis and reporting. "
        "You are meticulous, precise, and always provide actionable insights. "
        "Your task is to provide a comprehensive, structured explanation of data given its summary."
    )
)

aether_explain_agent = Agent(
    model,
    output_type=AetherExplainOutput,
    instructions=(
        "Given the statistical test details and results, provide a clear, concise, "
        "and jargon-free explanation. Include the significance, implications, limitations, "
        "and suggest follow-up actions. Tailor the explanation for a general technical audience."
        "\n\nContext and Results: {analysis_context}" # Placeholder for CLI to insert context
    ),
    system_prompt=(
        "You are an experienced data storyteller and statistical communicator. "
        "Your goal is to translate complex statistical outputs into understandable and actionable insights "
        "for non-statisticians and technical stakeholders. Be precise but accessible."
    )
)

aether_insight_agent = Agent(
    model,
    output_type=AetherInsightOutput,
    instructions=(
        "Analyze the provided statistical summary of a dataset and identify key insights, "
        "patterns, potential anomalies, and significant relationships. "
        "Offer actionable recommendations based on your findings."
        "\n\nData Summary: {data_summary}" # Placeholder for CLI to insert data summary
    ),
    system_prompt=(
        "You are a proactive data exploration expert and an anomaly detection specialist. "
        "You have a keen eye for hidden patterns and unusual occurrences in data. "
        "Your output should be informative, surprising where appropriate, and directly actionable."
    )
)

aether_hypothesize_agent = Agent(
    model,
    output_type=AetherHypothesizeOutput,
    instructions=(
        "Based on the provided dataset characteristics (columns, types, summary statistics), "
        "propose a list of plausible and testable statistical hypotheses. "
        "For each hypothesis, suggest the most appropriate statistical test(s) and explain your reasoning."
        "\n\nDataset Characteristics: {dataset_characteristics}" # Placeholder for CLI to insert characteristics
    ),
    system_prompt=(
        "You are a seasoned research methodologist and statistical consultant. "
        "You excel at framing data questions into testable hypotheses and recommending "
        "the most suitable analytical approaches. Think critically about common statistical inquiries "
        "relevant to the data types presented."
    )
)

aether_command_suggest_agent = Agent(
    model,
    output_type=AetherCommandSuggestOutput,
    instructions=(
        "The user wants to perform a data analysis task using AetherStats CLI. "
        "Given their natural language query and context about the available data, "
        "generate a list of precise AetherStats CLI commands that would fulfill their request. "
        "If the query is ambiguous, ask for clarification instead of guessing."
        "\n\nUser Query: {user_query}" # Placeholder for CLI to insert user query
        "\n\nAvailable Data/Context: {available_data_context}" # Placeholder for CLI to insert context (e.g., column names)
        "\n\nExamples of AetherStats commands:\n"
        "aetherstats describe <column>\n"
        "aetherstats visualize <column> --type <plot_type>\n"
        "aetherstats analyze ttest --group <group_column> --value <value_column>\n"
        "aetherstats clean missing --strategy <strategy> --column <column>\n"
        "aetherstats register <file_path> --type <data_type>\n"
    ),
    system_prompt=(
        "You are an intelligent CLI assistant for AetherStats. "
        "Your primary function is to translate human language data analysis requests "
        "into exact and executable AetherStats CLI commands. "
        "Be precise, adhere strictly to the command syntax, and provide concise explanations. "
        "Always prioritize asking for clarification if the request is unclear or requires more information."
    )
)

# NEW Agents (defined with correct Agent class)
aether_analysis_agent = Agent(
    model,
    output_type=AnalysisOutput,
    instructions=(
        "Perform a conceptual statistical analysis based on the provided data summary and analysis request. "
        "Return structured results including a summary, p-value (if applicable), interpretation, "
        "key metrics, and notes on assumptions. Also provide an overall conclusion and suggested follow-up. "
        "Do not actually run code, but describe the likely outcome of such an analysis given the data characteristics."
    ), # CORRECTED: Removed "{analysis_request}" from instructions
    system_prompt=(
        "You are a highly experienced data analyst and statistician. "
        "Your role is to understand statistical requests, interpret data characteristics, "
        "and provide insightful, structured analysis summaries as if you have performed the analysis. "
        "Be accurate in your statistical interpretations and clear in your conclusions."
    )
)

aether_code_generation_agent = Agent(
    model,
    output_type=CodeGenerationOutput,
    instructions=(
        "Generate complete, executable Python code to perform the specified data task. "
        "Include all necessary imports. If Pandas is suitable for the task, use it. "
        "Provide an explanation of the code, list required packages, and suggest a filename. "
        "Focus on best practices and readability. Do not include placeholder comments beyond initial function/class definitions."
        "\n\nTask and Data Context: {code_request_prompt}" # Placeholder for CLI to insert prompt
    ),
    system_prompt=(
        "You are an expert Python programmer specializing in data science and statistical computing. "
        "You generate clean, efficient, and well-commented Python code for data manipulation, "
        "analysis, and visualization. You understand common data libraries (e.g., pandas, numpy, scikit-learn, scipy, matplotlib, seaborn) "
        "and apply them appropriately."
    )
)

aether_report_agent = Agent(
    model,
    output_type=MarkdownReportOutput,
    instructions=(
        "Generate a professional, well-structured Markdown report based on the provided elements. "
        "The report should include a clear title, a brief summary, and logical sections "
        "for data overview, analysis results, and any custom sections. "
        "Use appropriate Markdown headings (e.g., #, ##, ###) and formatting (bold, italics, lists) for readability. "
        "Synthesize information to provide a coherent narrative and highlight key findings. "
        "Make sure the report is self-contained and clear."
        "\n\nReport Elements: {report_prompt_elements}" # Placeholder for CLI to insert elements
    ),
    system_prompt=(
        "You are an experienced technical writer and data science communicator. "
        "Your expertise lies in transforming raw data and analysis results into compelling "
        "and easy-to-understand reports for various audiences. "
        "You excel at structuring information logically and using Markdown effectively."
    )
)