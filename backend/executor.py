# executor.py
"""
Execute an approved plan against the workbook.
Passes session_id down so writes also back up to Supabase Storage.
"""


def execute_approved_plan(plan, workbook_path, session_id=None, filename=None):
    """
    Executes the plan on the given workbook.
    If session_id is provided, the file is uploaded to Supabase after every save.
    """
    import agent as agent_module
    agent_module.FILE_PATH = workbook_path

    # Pass session info to agent so it forwards to safe_save
    if hasattr(agent_module, "SESSION_ID"):
        agent_module.SESSION_ID = session_id
    else:
        agent_module.SESSION_ID = session_id

    if filename:
        agent_module.FILENAME = filename
    else:
        import os
        agent_module.FILENAME = os.path.basename(workbook_path)

    from agent import execute_plan

    print("\n===== EXECUTING APPROVED PLAN =====")
    print(f"Workbook: {workbook_path}")
    print(f"Session:  {session_id}")
    print(f"Filename: {getattr(agent_module, 'FILENAME', None)}")
    for i, step in enumerate(plan.get("steps", []), start=1):
        print(f"Step {i}: {step.get('tool')}")

    result = execute_plan(plan, plan)

    return {
        "success": result.get("success", False),
        "executed_steps": result.get("executed_steps", []),
        "error": result.get("error"),
    }