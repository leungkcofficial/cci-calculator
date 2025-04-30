from typing import Dict, List, Tuple
import logging
from app.config import mapping_config

# Configure logger
logger = logging.getLogger(__name__)

# Define default hierarchy rules
DEFAULT_HIERARCHY_RULES = [
    {
        "id": "rule_1",
        "name": "Hemiplegia/Paraplegia trumps Cerebrovascular Disease",
        "primary_condition": "hemiplegia_paraplegia",
        "secondary_condition": "cerebrovascular_disease",
        "action": "zero_secondary_if_primary"
    },
    {
        "id": "rule_2",
        "name": "Severe Liver Disease trumps Mild Liver Disease",
        "primary_condition": "liver_severe",
        "secondary_condition": "mild_liver_disease",
        "action": "zero_secondary_if_primary"
    },
    {
        "id": "rule_3",
        "name": "Diabetes with Complications trumps Diabetes without Complications",
        "primary_condition": "diabetes_w_complication",
        "secondary_condition": "diabetes_wo_complication",
        "action": "zero_secondary_if_primary"
    },
    {
        "id": "rule_4",
        "name": "Severe Renal Disease trumps Mild/Moderate Renal Disease",
        "primary_condition": "renal_severe",
        "secondary_condition": "renal_mild_moderate",
        "action": "zero_secondary_if_primary"
    },
    {
        "id": "rule_5",
        "name": "Metastatic Cancer trumps Malignancy",
        "primary_condition": "metastatic_cancer",
        "secondary_condition": "any_malignancy",
        "action": "zero_secondary_if_primary"
    },
    {
        "id": "rule_6",
        "name": "AIDS trumps HIV",
        "primary_condition": "aids",
        "secondary_condition": "hiv",
        "action": "zero_secondary_if_primary"
    }
]

# Initially set to default rules
HIERARCHY_RULES = DEFAULT_HIERARCHY_RULES.copy()

# Load hierarchy rules from configuration if available
if mapping_config and 'hierarchy_rules' in mapping_config:
    logger.info("Using hierarchy rules from config file")
    HIERARCHY_RULES = mapping_config['hierarchy_rules']
else:
    logger.warning("No hierarchy rules found in config, using default rules")


def apply_hierarchy_rules(conditions: Dict[str, int]) -> Tuple[Dict[str, int], List[str]]:
    """
    Applies the hierarchy rules to the condition flags.
    
    Args:
        conditions: Dictionary mapping CCI conditions to binary flags (0 or 1)
        
    Returns:
        Tuple containing:
        - Updated conditions dictionary after applying hierarchy rules
        - List of rule IDs that were applied
    """
    applied_rules = []
    
    # Create a copy of the conditions to avoid modifying the input
    updated_conditions = conditions.copy()
    
    # Apply each rule in order
    for rule in HIERARCHY_RULES:
        primary_condition = rule["primary_condition"]
        secondary_condition = rule["secondary_condition"]
        
        # Check if the primary condition is present
        if updated_conditions.get(primary_condition, 0) == 1:
            # If the secondary condition is also present, apply the rule
            if updated_conditions.get(secondary_condition, 0) == 1:
                # Zero out the secondary condition
                updated_conditions[secondary_condition] = 0
                # Record that this rule was applied
                applied_rules.append(rule["id"])
    
    return updated_conditions, applied_rules


def get_rule_by_id(rule_id: str) -> Dict:
    """
    Gets a rule by its ID.
    
    Args:
        rule_id: The ID of the rule to get
        
    Returns:
        The rule dictionary
        
    Raises:
        ValueError: If the rule ID is not found
    """
    for rule in HIERARCHY_RULES:
        if rule["id"] == rule_id:
            return rule
    
    raise ValueError(f"Rule with ID {rule_id} not found")


def get_rule_description(rule_id: str) -> str:
    """
    Gets a human-readable description of a rule.
    
    Args:
        rule_id: The ID of the rule to describe
        
    Returns:
        A string describing the rule
    """
    try:
        rule = get_rule_by_id(rule_id)
        return rule["name"]
    except ValueError:
        return f"Unknown rule: {rule_id}"


def validate_rules() -> bool:
    """
    Validates the hierarchy rules for consistency.
    Checks for circular dependencies and other issues.
    
    Returns:
        True if the rules are valid, False otherwise
    """
    # Check for duplicate rule IDs
    rule_ids = [rule["id"] for rule in HIERARCHY_RULES]
    if len(rule_ids) != len(set(rule_ids)):
        return False
    
    # Check for circular dependencies
    dependency_graph = {}
    for rule in HIERARCHY_RULES:
        primary = rule["primary_condition"]
        secondary = rule["secondary_condition"]
        
        if primary not in dependency_graph:
            dependency_graph[primary] = []
        
        dependency_graph[primary].append(secondary)
    
    # Check for cycles in the dependency graph
    visited = set()
    path = set()
    
    def has_cycle(node):
        if node in path:
            return True
        if node in visited:
            return False
        
        visited.add(node)
        path.add(node)
        
        for neighbor in dependency_graph.get(node, []):
            if has_cycle(neighbor):
                return True
        
        path.remove(node)
        return False
    
    for node in dependency_graph:
        if has_cycle(node):
            return False
    
    return True


# Validate the hierarchy rules after they're loaded
if not validate_rules():
    logger.error("Hierarchy rules validation failed, using default rules")
    HIERARCHY_RULES = DEFAULT_HIERARCHY_RULES.copy()