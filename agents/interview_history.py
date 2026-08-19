from supabase import Client


def get_interview_history(user_id: str, supabase: Client):

    # Get previous interview sessions
    conversations = (
        supabase
        .table("conversations")
        .select("id, title, target_role, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    if not conversations.data:
        return {
            "found": False,
            "message": "No previous interviews found."
        }

    history = []

    for conversation in conversations.data:

        # Get messages belonging to this interview
        messages = (
            supabase
            .table("messages")
            .select("role, content, created_at")
            .eq("conversation_id", conversation["id"])
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )

        history.append({
            "conversation_id": conversation["id"],
            "target_role": conversation.get("target_role"),
            "created_at": conversation["created_at"],
            "messages": messages.data
        })

    return {
        "found": True,
        "interviews": history
    }