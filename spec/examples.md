# Example Payloads And Spotify Auth Notes

## Example Spotify URI

```text
spotify:track:23dfqX3nRspRfHtVgOVU95
```

## One-Time Refresh Token Flow

Add this redirect URI to your Spotify app:

```text
http://127.0.0.1:8000/callback
```

Open an authorization URL like this in your browser:

```text
https://accounts.spotify.com/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fcallback&scope=user-modify-playback-state%20user-read-playback-state
```

After approval, Spotify redirects to a URL like:

```text
http://127.0.0.1:8000/callback?code=PASTE_CODE_HERE
```

Exchange that code for tokens:

```sh
curl -s -u "$JUKEBOX_SPOTIFY_CLIENT_ID:$JUKEBOX_SPOTIFY_CLIENT_SECRET" \
  -d grant_type=authorization_code \
  -d code='PASTE_CODE_HERE' \
  --data-urlencode redirect_uri='http://127.0.0.1:8000/callback' \
  https://accounts.spotify.com/api/token
```

Store the returned `refresh_token` in `.env` and do not commit the response payload.
