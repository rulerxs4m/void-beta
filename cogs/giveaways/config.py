def parse_csv_roles(text: str) -> list[int]:
    """Parse CSV role IDs from string, return as list of ints."""
    if not text:
        return []
    return [int(r) for r in text.split(',') if r.strip().isdigit()]

def to_csv_roles(roles: list[int]) -> str:
    """Convert list of role IDs to CSV string."""
    return ','.join(str(r) for r in roles)

def bool_to_int(val: bool) -> int:
    return 1 if val else 0

def int_to_bool(val: int) -> bool:
    return val == 1
