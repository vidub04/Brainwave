from supabase import Client


def get_resume_details(user_id: str, supabase: Client):
    result = (
        supabase
        .table("resumes")
        .select("structured")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return {
            "found": False,
            "message": "No resume found for this user."
        }

    return {
        "found": True,
        "resume": result.data[0]["structured"]
    }