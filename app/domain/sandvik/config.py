"""
Sandvik machine configuration.

This module defines the available machine groups and devices for the Sandvik API.
"""

from app.domain.sandvik.models import MachineConfig, MachineGroup

# Machine groups configuration
MACHINE_GROUPS = {
    "DMC_100": MachineGroup(
        display_name="DMC 100 (Machines 1-4)",
        devices=[
            "produitsgilbert_DMC_100_01_5a1286",
            "produitsgilbert_DMC_100_02_3c11c4",
            "produitsgilbert_DMC_100_03_9ad22c",
            "produitsgilbert_DMC_100_04_d81500",
        ],
    ),
    "NLX2500": MachineGroup(
        display_name="NLX-2500 (Machines 1-5)",
        devices=[
            "produitsgilbert_NLX-2500-01_1f62d2",
            "produitsgilbert_NLX-2500-02_c48076",
            "produitsgilbert_NLX-2500-03_7db86c",
            "produitsgilbert_NLX-2500-04_aae59b",
            "produitsgilbert_NLX-2500-05_1291f0",
        ],
    ),
    "MZ350": MachineGroup(
        display_name="TOU-MZ350 (Machines 1-3)",
        devices=[
            "produitsgilbert_TOU-MZ350-01_dd405f",
            "produitsgilbert_TOU-MZ350-02_97ae33",
            "produitsgilbert_TOU-MZ350-03_f3e3e6",
        ],
    ),
    "DMC_340": MachineGroup(
        display_name="DMC 340 (Machine 1)",
        devices=["produitsgilbert_DMC_340_01_53afe9"],
    ),
    "DEC_370": MachineGroup(
        display_name="DEC 370 (Machine 1)",
        devices=["produitsgilbert_DEC_370_01_90441a"],
    ),
    "MTV_655": MachineGroup(
        display_name="MTV 655 (Machine 1)",
        devices=["produitsgilbert_MTV_655_01_65b08f"],
    ),
}

# Complete machine configuration
MACHINE_CONFIG = MachineConfig(groups=MACHINE_GROUPS)


def get_machine_config() -> MachineConfig:
    """Get the complete machine configuration."""
    return MACHINE_CONFIG


def get_machine_group_names() -> list[str]:
    """Get list of available machine group names."""
    return list(MACHINE_GROUPS.keys())


def get_machine_group(group_name: str) -> MachineGroup:
    """Get a specific machine group by name."""
    if group_name not in MACHINE_GROUPS:
        raise ValueError(f"Machine group '{group_name}' not found")
    return MACHINE_GROUPS[group_name]


def get_all_machine_names() -> list[str]:
    """Get all machine device names across all groups."""
    all_machines = []
    for group in MACHINE_GROUPS.values():
        all_machines.extend(group.devices)
    return all_machines


def expand_machine_groups(machine_groups: list[str] = None) -> list[str]:
    """
    Expand machine group names to individual machine device names.

    Args:
        machine_groups: List of machine group names. If None, returns all machines.

    Returns:
        List of machine device names.
    """
    if machine_groups is None:
        return get_all_machine_names()

    machines = []
    for group_name in machine_groups:
        if group_name in MACHINE_GROUPS:
            machines.extend(MACHINE_GROUPS[group_name].devices)
        else:
            # If it's not a group name, treat it as a direct machine name
            machines.append(group_name)

    return machines
