from supabase import Client


def get_current_state(
    conversation_id: str,
    user_id: str,
    supabase: Client
):
    # Make sure this conversation belongs to the logged-in user
    conversation_result = (
        supabase
        .table("conversations")
        .select("id, target_role, created_at")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not conversation_result.data:
        return {
            "found": False,
            "message": "Interview session not found."
        }

    conversation = conversation_result.data[0]

    # Get messages from the current interview
    messages_result = (
        supabase
        .table("messages")
        .select("role, content, created_at")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )

    messages = messages_result.data

    # Count candidate answers
    user_messages = [
        message for message in messages
        if message["role"] == "user"
    ]

    # Get the latest candidate answer
    latest_answer = (
        user_messages[-1]["content"]
        if user_messages
        else None
    )

    return {
        "found": True,
        "conversation_id": conversation["id"],
        "target_role": conversation["target_role"],

        # Basic measurable state
        "questions_answered": len(user_messages),
        "next_question_number": len(user_messages) + 1,
        "total_main_questions": 11,

        # Latest response
        "latest_answer": latest_answer,

        # Give the model the conversation so it can reason
        # about follow-ups, interviewer turns, topics, etc.
        "messages": messages,

        "instruction": """
        Determine the current interview state from the conversation.

        You must decide:
        - whether the next question is a main question or follow-up
        - whether Alex or Ricky should speak next
        - what topic is currently being discussed
        - appropriate difficulty
        - whether to continue the current topic or move to a new topic

        Alex is the Senior Software Engineer.
        Ricky is the HR Manager.

        A follow-up should normally be asked by the same interviewer
        who asked the previous question.

        A follow-up should not increment the main question number.
        """
    }