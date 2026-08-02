from pathlib import Path

# 1. Fix test_inspection_service.py - add user_id to create_session call
p = Path("tests/unit/test_inspection_service.py")
text = p.read_text(encoding="utf-8")
old = 'result = await service.create_session(created.vehicle_id)'
new = 'result = await service.create_session(created.vehicle_id, user_id="00000000-0000-0000-0000-000000000099")'
if old in text:
    text = text.replace(old, new)
    # add assertion for user_id
    old2 = '    assert repos[0].create.call_args.args[0].status == "DRAFT"'
    new2 = '    assert repos[0].create.call_args.args[0].status == "DRAFT"\n    assert repos[0].create.call_args.args[0].user_id == "00000000-0000-0000-0000-000000000099"'
    if old2 in text:
        text = text.replace(old2, new2)
    p.write_text(text, encoding="utf-8")
    print("UPDATED tests/unit/test_inspection_service.py")
else:
    print("PATTERN NOT FOUND in inspection file")

# 2. Fix test_opportunity_repository.py - add user_id to Vehicle creation in test_list_returns_paginated
p2 = Path("tests/integration/database/test_opportunity_repository.py")
text2 = p2.read_text(encoding="utf-8")
old_v = 'v = Vehicle(\n                source="test",\n                external_id=f"ext_{i}",'
new_v = 'v = Vehicle(\n                user_id="00000000-0000-0000-0000-000000000099",\n                source="test",\n                external_id=f"ext_{i}",'
if old_v in text2:
    text2 = text2.replace(old_v, new_v)
    p2.write_text(text2, encoding="utf-8")
    print("UPDATED tests/integration/database/test_opportunity_repository.py")
else:
    print("PATTERN NOT FOUND in opportunity file")
