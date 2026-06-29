"""Facebook Reels upload via Graph API v21."""
import os
import requests
import time
from config import FB_APP_ID, FB_APP_SECRET, FB_PAGE_ID, FB_ACCESS_TOKEN


class FacebookUploader:
    """Upload videos as Facebook Reels via Graph API."""
    
    GRAPH_URL = "https://graph.facebook.com/v21.0"
    
    def __init__(self, access_token=None, page_id=None):
        self.access_token = access_token or FB_ACCESS_TOKEN
        self.page_id = page_id or FB_PAGE_ID
    
    def upload_reel(self, video_path, title="", description="",
                    access_token=None, page_id=None):
        """
        Upload a video as a Facebook Reel.
        Uses 3-phase upload: start → upload binary → finish.
        
        Returns dict with video_id and status.
        """
        token = access_token or self.access_token
        pid = page_id or self.page_id
        
        if not token:
            raise Exception("Facebook access token not set")
        if not pid:
            raise Exception("Facebook page ID not set")
        if not os.path.exists(video_path):
            raise Exception(f"Video file not found: {video_path}")
        
        file_size = os.path.getsize(video_path)
        
        # Phase 1: Start upload session
        start_url = f"{self.GRAPH_URL}/{pid}/video_reels"
        start_params = {
            "upload_phase": "start",
            "access_token": token
        }
        
        resp = requests.post(start_url, data=start_params)
        if resp.status_code != 200:
            raise Exception(f"Start upload failed: {resp.text}")
        
        start_data = resp.json()
        upload_session_id = start_data.get("upload_session_id")
        video_id = start_data.get("video_id")
        start_offset = int(start_data.get("start_offset", 0))
        end_offset = int(start_data.get("end_offset", file_size))
        
        if not upload_session_id:
            raise Exception(f"No upload_session_id in response: {start_data}")
        
        # Phase 2: Upload binary (chunked)
        chunk_size = 4 * 1024 * 1024  # 4MB chunks
        current_offset = start_offset
        
        with open(video_path, "rb") as f:
            while current_offset < file_size:
                f.seek(current_offset)
                chunk = f.read(chunk_size)
                chunk_len = len(chunk)
                
                upload_url = f"https://rupload.facebook.com/video-upload/v21.0/{video_id}"
                headers = {
                    "Authorization": f"OAuth {token}",
                    "offset": str(current_offset),
                    "file_size": str(file_size),
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(chunk_len)
                }
                
                resp = requests.post(upload_url, headers=headers, data=chunk)
                if resp.status_code != 200:
                    raise Exception(f"Upload chunk failed at offset {current_offset}: {resp.text}")
                
                current_offset += chunk_len
        
        # Phase 3: Finish upload (publish as Reel)
        finish_url = f"{self.GRAPH_URL}/{pid}/video_reels"
        finish_params = {
            "upload_phase": "finish",
            "upload_session_id": upload_session_id,
            "access_token": token,
            "title": title or "Drama China Sub Indo",
            "description": description or f"{title}\n\n#DramaChina #CDrama #SubtitleIndonesia #DramaChinaSubIndo",
            "video_state": "published"
        }
        
        resp = requests.post(finish_url, data=finish_params)
        if resp.status_code != 200:
            raise Exception(f"Finish upload failed: {resp.text}")
        
        finish_data = resp.json()
        
        return {
            "video_id": video_id,
            "status": "uploaded",
            "success": finish_data.get("success", False),
            "fb_response": finish_data
        }
    
    def get_page_info(self, access_token=None, page_id=None):
        """Get Facebook page information."""
        token = access_token or self.access_token
        pid = page_id or self.page_id
        
        resp = requests.get(
            f"{self.GRAPH_URL}/{pid}",
            params={"fields": "name,fan_count,category", "access_token": token}
        )
        return resp.json()
    
    def get_auth_url(self, app_id=None, redirect_uri="https://localhost"):
        """Generate Facebook OAuth URL for page access token."""
        aid = app_id or FB_APP_ID
        scopes = [
            "pages_manage_posts",
            "pages_read_engagement", 
            "pages_show_list",
            "pages_manage_videos",
            "pages_manage_metadata"
        ]
        scope_str = ",".join(scopes)
        
        return (
            f"https://www.facebook.com/v21.0/dialog/oauth?"
            f"client_id={aid}&redirect_uri={redirect_uri}"
            f"&scope={scope_str}&response_type=code"
        )
    
    def exchange_code(self, code, app_id=None, app_secret=None, 
                      redirect_uri="https://localhost"):
        """Exchange OAuth code for short-lived token, then extend to long-lived."""
        aid = app_id or FB_APP_ID
        secret = app_secret or FB_APP_SECRET
        
        # Get short-lived token
        resp = requests.get(
            f"{self.GRAPH_URL}/oauth/access_token",
            params={
                "client_id": aid,
                "client_secret": secret,
                "redirect_uri": redirect_uri,
                "code": code
            }
        )
        data = resp.json()
        short_token = data.get("access_token")
        
        if not short_token:
            raise Exception(f"Failed to get token: {data}")
        
        # Extend to long-lived token (60 days)
        resp = requests.get(
            f"{self.GRAPH_URL}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": aid,
                "client_secret": secret,
                "fb_exchange_token": short_token
            }
        )
        
        long_data = resp.json()
        return {
            "access_token": long_data.get("access_token", short_token),
            "token_type": "long_lived",
            "expires_in": long_data.get("expires_in", 5184000)
        }
    
    def get_page_token(self, user_token, page_id=None):
        """Get page-specific access token from user token."""
        pid = page_id or self.page_id
        
        resp = requests.get(
            f"{self.GRAPH_URL}/me/accounts",
            params={"access_token": user_token}
        )
        data = resp.json()
        
        for page in data.get("data", []):
            if page.get("id") == pid:
                return {
                    "page_id": page["id"],
                    "page_name": page.get("name"),
                    "access_token": page["access_token"]
                }
        
        # Return all pages if specific one not found
        pages = data.get("data", [])
        if pages:
            return {
                "page_id": pages[0]["id"],
                "page_name": pages[0].get("name"),
                "access_token": pages[0]["access_token"],
                "all_pages": pages
            }
        
        raise Exception("No pages found. Make sure the user has admin access to a Facebook Page.")
