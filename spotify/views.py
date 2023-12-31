from django.shortcuts import render
from .credentials import REDIREICT_URI, CLIENT_ID, CLIENT_SECRET
from rest_framework.views import APIView
from rest_framework import generics
from requests import Request, post
from rest_framework import status
from rest_framework.response import Response
from .util import update_or_create_user_tokens, is_spotify_authenticated, execute_spotify_api_request, play_song, pause_song, skip_song

from django.shortcuts import redirect, render
from .models import SpotifyToken
from .serializers import TokenSerializer
from api.models import Room 
from .models import Vote



# Create your views here.
class AuthURL(APIView):
    def get(self, request, format = None):
        scropes = 'user-read-playback-state user-modify-playback-state user-read-currently-playing' #this comes from Spotify API Documentation

        url = Request('Get', 'https://accounts.spotify.com/authorize', params= {
            'scope': scropes, 
            'response_type': 'code',
            'redirect_uri' : REDIREICT_URI,
            'client_id': CLIENT_ID
        }).prepare().url

        return Response({'url': url}, status =status.HTTP_200_OK )
    
def spotify_callback(request, format = None):
    code = request.GET.get('code')
    error = request.GET.get('error')

    response = post('https://accounts.spotify.com/api/token', data = {
        'grant_type' : 'authorization_code',
        'code' : code, # Once we are authorized on spotify, they send us a code to get another code
        'redirect_uri' : REDIREICT_URI,
        'client_id': CLIENT_ID,
        'client_secret' : CLIENT_SECRET
    }).json()
    access_token = response.get('access_token')  #We get an access token 
    token_type = response.get('token_type') # 
    refresh_token = response.get('refresh_token') # A refresh token
    expires_in = response.get('expires_in') # When it expires
    error = response.get('error')

    # We get all these tokens once we are authorized on spotify 

    if not request.session.exists(request.session.session_key):
        request.session.create()


    update_or_create_user_tokens(request.session.session_key, access_token, token_type, expires_in, refresh_token) #Update sessionid with the new tokens and redirect to front end 
    return redirect('frontend:')


class isAuthenticated(APIView):
    def get(self, request, format = None):
        is_authenticated = is_spotify_authenticated(
            self.request.session.session_key)
        return Response({'status': is_authenticated}, status=status.HTTP_200_OK)

class modelView(generics.ListAPIView):
    queryset = SpotifyToken.objects.all()
    serializer_class = TokenSerializer

class CurrentSong(APIView):
    def get(self, request, format = None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code=room_code)
        if room.exists():
            room = room[0]
        else:   
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        host = room.host
        endpoint = "player/currently-playing"
        response = execute_spotify_api_request(host, endpoint)

        NoSong = {
            'title': "No Song Playing :(",
            'artist' : "Start a song on your nearest spotify App to see", 
            'duration': 0,
            'time': 0,
            'image_url': "https://i.scdn.co/image/ab67616d00001e02ff9ca10b55ce82ae553c8228",
            'is_playing': False,
            'votes': 0,
            'votes_required': room.votes_to_skip,
            'id': "None"
        }

        if "EMPTY_RESPONSE" in response or 'item' not in response or response == "":
            return Response(NoSong, status=status.HTTP_200_OK)
        
        item = response.get('item')
        duration = item.get('duration_ms')
        progress = response.get('progress_ms')
        album_cover = item.get('album').get('images')[0].get('url')
        is_playing = response.get('is_playing')
        song_id = item.get('id')

        # create string of artist seperated by commas
        artist_string = ""
        for i, artist in enumerate(item.get('artists')):
            if i > 0:
                artist_string += ", "
            name = artist.get('name')
            artist_string += name
        votes = len(Vote.objects.filter(room=room, song_id=song_id) )
        song = {
            'title': item.get('name'),
            'artist' : artist_string, 
            'duration': duration,
            'time': progress,
            'image_url': album_cover,
            'is_playing': is_playing,
            'votes': votes,
            'votes_required': room.votes_to_skip,
            'id': song_id
        }
        self.update_room_song(room, song_id)

        return Response(song, status=status.HTTP_200_OK)
    
    def update_room_song(self, room, song_id):
        current_song= room.current_song
        if current_song != song_id:
            room.current_song = song_id
            room.save(update_fields =['current_song'])
            votes = Vote.objects.filter(room= room).delete() # Delete all vote objects with this room associated


class PauseSong(APIView):
    def put(self, response, format = None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code = room_code)[0]
        if self.request.session.session_key == room.host or room.guest_can_pause:
            pause_song(room.host)
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        return Response({}, status=status.HTTP_403_FORBIDDEN)
    
class PlaySong(APIView):
    def put(self, response, format = None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code = room_code)[0]
        if self.request.session.session_key == room.host or room.guest_can_pause:
            play_song(room.host)
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        return Response({}, status=status.HTTP_403_FORBIDDEN)
    
class SkipSong(APIView):
    # Adding a new vote, we are adding to a model
    def post(self, request, format=None):
        room_code = self.request.session.get('room_code') #get code from request
        room = Room.objects.filter(code = room_code)[0] # Now bring in rest of internal code details
        votes = Vote.objects.filter(room=room, song_id=room.current_song) #Make sure you are grabbing votes for current song 
        votes_needed = room.votes_to_skip

        if self.request.session.session_key == room.host or len(votes) + 1 >= votes_needed:
            votes.delete() #clear all votes associated with this room and current song
            skip_song(room.host)
        else:
            if len(Vote.objects.filter(user = self.request.session.session_key)) < 1:
                vote = Vote(user=self.request.session.session_key,
                        room=room, song_id=room.current_song)
                vote.save()
        return Response({}, status=status.HTTP_204_NO_CONTENT)
    
class deleteVote(APIView):
    def post(self, request, format =  None):
        vote  = Vote.objects.filter(user=self.request.session.session_key)[0]
        if vote:
            Vote.objects.filter(user=self.request.session.session_key).delete()

        return Response({}, status=status.HTTP_204_NO_CONTENT)

            