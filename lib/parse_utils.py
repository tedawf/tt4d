def split_outlet_address(location_str: str):
    location_str = location_str.strip()

    # it works cos of the last " - ", unit number no count
    parts = location_str.rsplit(" - ", 1)

    if len(parts) == 2:
        outlet_name, address = parts
    else:
        outlet_name, address = location_str, "-"  # No address found

    return outlet_name, address
