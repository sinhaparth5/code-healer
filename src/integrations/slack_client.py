from typing import Dict, List, Optional, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from utils.logger import get_logger

logger = get_logger(__name__)


class SlackClient:
    def __init__(self, token: str):
        self.client = WebClient(token=token)
        self.user_id = None
        self._get_bot_user_id()

    def _get_bot_user_id(self):
        try:
            response = self.client.auth_test()
            self.user_id = response["user_id"]
        except SlackApiError as e:
            logger.error(f"Failed to get bot user ID: {e}")

    def search_messages(
        self,
        query: str,
        count: int = 20,
        sort: str = "timestamp",
        sort_dir: str = "desc"
    ) -> List[Dict[str, Any]]:
        try:
            response = self.client.search_messages(
                query=query,
                count=count,
                sort=sort,
                sort_dir=sort_dir
            )
            
            messages = []
            for match in response.get("messages", {}).get("matches", []):
                messages.append({
                    "text": match.get("text", ""),
                    "user": match.get("user", ""),
                    "username": match.get("username", ""),
                    "timestamp": match.get("ts", ""),
                    "channel": match.get("channel", {}).get("id", ""),
                    "channel_name": match.get("channel", {}).get("name", ""),
                    "permalink": match.get("permalink", "")
                })
            
            return messages
        except SlackApiError as e:
            logger.error(f"Failed to search messages: {e}")
            return []

    def get_conversation_history(
        self,
        channel_id: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            response = self.client.conversations_history(
                channel=channel_id,
                limit=limit,
                oldest=oldest,
                latest=latest
            )
            
            return [
                {
                    "text": msg.get("text", ""),
                    "user": msg.get("user", ""),
                    "timestamp": msg.get("ts", ""),
                    "thread_ts": msg.get("thread_ts"),
                    "reply_count": msg.get("reply_count", 0)
                }
                for msg in response.get("messages", [])
            ]
        except SlackApiError as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=limit
            )
            
            return [
                {
                    "text": msg.get("text", ""),
                    "user": msg.get("user", ""),
                    "timestamp": msg.get("ts", "")
                }
                for msg in response.get("messages", [])
            ]
        except SlackApiError as e:
            logger.error(f"Failed to get thread replies: {e}")
            return []

    def post_message(
        self,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
                thread_ts=thread_ts
            )
            return {
                "ts": response["ts"],
                "channel": response["channel"]
            }
        except SlackApiError as e:
            logger.error(f"Failed to post message: {e}")
            return None

    def update_message(
        self,
        channel: str,
        ts: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        try:
            self.client.chat_update(
                channel=channel,
                ts=ts,
                text=text,
                blocks=blocks
            )
            return True
        except SlackApiError as e:
            logger.error(f"Failed to update message: {e}")
            return False

    def add_reaction(self, channel: str, timestamp: str, reaction: str) -> bool:
        try:
            self.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=reaction
            )
            return True
        except SlackApiError as e:
            logger.error(f"Failed to add reaction: {e}")
            return False

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.users_info(user=user_id)
            user = response["user"]
            return {
                "id": user["id"],
                "name": user["name"],
                "real_name": user.get("real_name", ""),
                "is_bot": user.get("is_bot", False),
                "is_admin": user.get("is_admin", False)
            }
        except SlackApiError as e:
            logger.error(f"Failed to get user info: {e}")
            return None

    def list_channels(self, types: str = "public_channel,private_channel") -> List[Dict[str, Any]]:
        try:
            response = self.client.conversations_list(types=types)
            return [
                {
                    "id": channel["id"],
                    "name": channel["name"],
                    "is_private": channel.get("is_private", False),
                    "is_archived": channel.get("is_archived", False)
                }
                for channel in response.get("channels", [])
            ]
        except SlackApiError as e:
            logger.error(f"Failed to list channels: {e}")
            return []

    def search_for_solutions(
        self,
        error_keywords: List[str],
        channels: Optional[List[str]] = None,
        time_window_days: int = 180
    ) -> List[Dict[str, Any]]:
        solution_indicators = ["fixed", "resolved", "solution", "solved", "worked"]
        
        query_parts = error_keywords + solution_indicators
        query = " OR ".join([f'"{kw}"' for kw in query_parts])
        
        if channels:
            channel_filter = " OR ".join([f"in:#{ch}" for ch in channels])
            query = f"({query}) AND ({channel_filter})"
        
        messages = self.search_messages(query, count=50)
        
        solutions = []
        for msg in messages:
            if any(indicator in msg["text"].lower() for indicator in solution_indicators):
                thread_messages = []
                if msg.get("thread_ts"):
                    thread_messages = self.get_thread_replies(
                        msg["channel"],
                        msg["thread_ts"]
                    )
                
                code_blocks = self._extract_code_blocks(msg["text"])
                for thread_msg in thread_messages:
                    code_blocks.extend(self._extract_code_blocks(thread_msg["text"]))
                
                user_info = self.get_user_info(msg["user"]) if msg.get("user") else None
                
                solutions.append({
                    "text": msg["text"],
                    "channel": msg["channel_name"],
                    "user": user_info,
                    "timestamp": msg["timestamp"],
                    "permalink": msg["permalink"],
                    "thread_messages": thread_messages,
                    "code_blocks": code_blocks,
                    "relevance_score": self._calculate_relevance(msg, error_keywords)
                })
        
        solutions.sort(key=lambda x: x["relevance_score"], reverse=True)
        return solutions

    def send_incident_notification(
        self,
        channel: str,
        incident_id: str,
        failure_type: str,
        service: str,
        error_summary: str,
        automated_action: Optional[str] = None
    ) -> Optional[str]:
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Deployment Failure Detected: {incident_id}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Service:*\n{service}"},
                    {"type": "mrkdwn", "text": f"*Type:*\n{failure_type}"},
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error:*\n```{error_summary}```"
                }
            }
        ]
        
        if automated_action:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Automated Action:*\n{automated_action}"
                }
            })
        
        result = self.post_message(channel=channel, blocks=blocks)
        return result["ts"] if result else None

    def send_resolution_update(
        self,
        channel: str,
        thread_ts: str,
        status: str,
        details: str
    ) -> bool:
        emoji_map = {
            "success": "✅",
            "failed": "❌",
            "in_progress": "⏳"
        }
        
        text = f"{emoji_map.get(status, '🔔')} *Resolution Update:* {status}\n{details}"
        
        return self.post_message(
            channel=channel,
            text=text,
            thread_ts=thread_ts
        ) is not None

    def _extract_code_blocks(self, text: str) -> List[str]:
        import re
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        return matches

    def _calculate_relevance(self, message: Dict[str, Any], keywords: List[str]) -> float:
        text = message["text"].lower()
        keyword_matches = sum(1 for kw in keywords if kw.lower() in text)
        
        score = keyword_matches * 10
        
        if message.get("thread_messages"):
            score += len(message["thread_messages"]) * 2
        
        if message.get("code_blocks"):
            score += len(message["code_blocks"]) * 5
        
        return score
