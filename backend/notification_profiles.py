"""Helpers for reusable notification destination profiles."""


def resolve_notification_destination(destination, settings):
    """Resolve an app destination reference to its saved profile."""
    if not isinstance(destination, dict):
        return None, "Each notification destination must be an object"

    profile_id = str(destination.get("profile_id", "")).strip()
    if not profile_id:
        return dict(destination), None

    profiles = (settings or {}).get("notification_profiles", [])
    if not isinstance(profiles, list):
        return None, "Notification profiles setting must be an array"

    profile = next(
        (
            item
            for item in profiles
            if isinstance(item, dict) and str(item.get("id", "")).strip() == profile_id
        ),
        None,
    )
    if profile is None:
        return None, f"Notification profile not found: {profile_id}"

    resolved = {
        key: value
        for key, value in profile.items()
        if key not in {"id", "name", "profile_id"}
    }
    return resolved, None


def validate_notification_profiles(profiles, settings, destination_validator):
    """Validate profile identity and the concrete destination in each profile."""
    if not isinstance(profiles, list):
        return False, "notification_profiles must be an array"

    seen_ids = set()
    seen_names = set()
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            return False, f"Notification profile {index + 1} must be an object"

        profile_id = str(profile.get("id", "")).strip()
        name = str(profile.get("name", "")).strip()
        if not profile_id:
            return False, f"Notification profile {index + 1} requires an id"
        if not name:
            return False, f"Notification profile {index + 1} requires a name"
        if profile_id in seen_ids:
            return False, f"Duplicate notification profile id: {profile_id}"
        if name.casefold() in seen_names:
            return False, f"Duplicate notification profile name: {name}"
        if profile.get("profile_id"):
            return False, "Notification profiles cannot reference another profile"

        seen_ids.add(profile_id)
        seen_names.add(name.casefold())
        destination = {
            key: value
            for key, value in profile.items()
            if key not in {"id", "name", "profile_id"}
        }
        is_valid, error = destination_validator(destination, settings)
        if not is_valid:
            return False, f'Notification profile "{name}": {error}'

    return True, None
