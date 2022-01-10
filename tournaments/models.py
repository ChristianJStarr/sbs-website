import io
import os
import uuid
from datetime import datetime
from time import time
from urllib.request import urlopen

import quickle
import requests
from PIL import Image
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.utils import timezone

from ScratchBowling import settings
from ScratchBowling.sbs_utils import is_valid_uuid
from centers.models import Center
from tournaments.scraping.soup_parser import update_tournament_with_soup

User = get_user_model()






class Tournament(models.Model):
    tournament_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)

    scoring_data_id = models.UUIDField(editable=True, blank=True, null=True)
    center = models.ForeignKey('centers.Center', blank=True, on_delete=models.SET_NULL, null=True, related_name='tournaments')
    format_id = models.UUIDField(editable=True, unique=True, blank=True, null=True)
    oil_patterns = models.ManyToManyField('oils.Oil_Pattern', blank=True, related_name='tournaments')
    vod_id = models.UUIDField(editable=True, unique=False, null=True, blank=True)

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    datetime = models.DateField(default=timezone.now, editable=True)
    picture = models.ImageField(default='tournament-pictures/default.jpg', upload_to='tournament-pictures/')



    entry_fee = models.FloatField(blank=True, null=True)
    total_games = models.IntegerField(null=False, blank=True, default=0)
    qualifiers = models.JSONField(blank=True, null=True)
    matchplay = models.JSONField(blank=True, null=True)
    sponsor =  models.UUIDField(editable=True, unique=False, null=True, blank=True)
    finished = models.BooleanField(default=False)
    live = models.BooleanField(default=False)
    team_size = models.SmallIntegerField(default=1)

    stream_available = models.BooleanField(default=False)

    tournament_data = models.BinaryField(blank=True, null=True)
    placement_data = models.BinaryField(blank=True, null=True)


    data_scoring = models.BinaryField(blank=True, null=True)

    spots_reserved = models.IntegerField(null=False, blank=True, default=0)

    live_status_header = models.TextField(blank=True, null=True)
    live_status_leader = models.UUIDField(editable=True, unique=False, null=True, blank=True)
    live_status_leader_score = models.FloatField(default=0, blank=True)

    # <editor-fold desc="-- SCRAPING --">
    scraped = models.BooleanField(default=False)
    soup_url = models.TextField(default='')
    soup = models.TextField(default='')
    @classmethod
    def update_all(cls, logging=False):
        base_url = 'https://www.scratchbowling.com'
        page = 0
        soup_urls = []
        while True:
            with urlopen(base_url + '/tournament-results?page=' + str(page)) as response:
                if logging:
                    print('Scanning Page ' + str(page))
                soup = BeautifulSoup(response, 'lxml')
                data = soup.find_all(class_='node__title')
                if data:
                    for node in data:
                        tag = node.find('a')
                        if tag:
                            url = tag.get('href')
                            if url and '/tournament/' in url:
                                soup_urls.append(base_url + url)
                    page += 1
                else:
                    break

        with urlopen(base_url + '/upcoming-tournaments') as response:
            soup = BeautifulSoup(response, 'lxml')
            data = soup.find_all('td')
            for node in data:
                tag = node.find('a')
                if tag:
                    link = tag.get('href')
                    if link and '/tournament/' in link:
                        soup_urls.append(link)

        if logging:
            print('Found ' + str(len(soup_urls)) + ' soup urls.')

        tournaments = []
        count = 0
        for soup_url in soup_urls:
            tournament = cls.objects.filter(soup_url=soup_url).first()
            if tournament:
                continue
            tournament = cls(soup_url=soup_url, scraped=True)
            if tournament and tournament.make_soup() and tournament.eat_soup():
                tournaments.append(tournament)
                if logging:
                    count += 1
                    print('Making Soup ' + str(count))

        if logging:
            print('Saving ' + str(len(tournaments)) + ' Tournaments')

        cls.objects.bulk_create(tournaments, 200)

        if logging:
            print('Update All Complete')

    @classmethod
    def only_eat_all(cls, logging=False):
        if logging:
            start_time = time()
        tournaments = cls.objects.filter(scraped=True)
        for tournament in tournaments:
            if tournament.soup and tournament.eat_soup():
                tournament.save()
                if logging:
                    print('Updated: ' + str(tournament.tournament_id)[:6])
        if logging:
            end_time = time()
            print('Updated ' + str(len(tournaments)) + ' in ' + str(round((end_time - start_time) / 60, 3)) + 'm')


    def make_soup(self):
        if self.soup_url:
            with urlopen(self.soup_url) as response:
                soup = BeautifulSoup(response, 'lxml')
                if soup:
                    body = soup.find('body')
                    if body:
                        self.soup = str(body)
                        return True
        return False
    def eat_soup(self):
        if self.soup:
            soup = BeautifulSoup(self.soup, 'html.parser')
            return update_tournament_with_soup(self, soup)
        return False
    # </editor-fold>






    @classmethod
    def create(cls, name):
        tournament = cls(tournament_name=name)
        return tournament

    @classmethod
    def get_tournament_by_uuid(cls, uuid):
        uuid = is_valid_uuid(uuid)
        if uuid:
            return cls.objects.filter(tournament_id=uuid).first()

    @classmethod
    def get_tournaments_by_uuid_list(cls, uuid_list):
        return cls.objects.filter(tournament_id__in=uuid_list)

    @classmethod
    def get_upcoming_tournaments(cls, amount=10, offset=0):
        return cls.objects.all().exclude(finished=True).exclude(live=True)[offset:offset+amount]


    # TOURNAMENT GET SPONSOR INFO
    def get_sponsor_image(self):
        return Sponsor.get_sponsor_image_uuid(self.sponsor)

    # TOURNAMENT HEADER PICTURE
    def get_picture(self):
        if self.has_default_picture():
            try:
                return '/media/' + str(self.download_scraped_image())
            except:
                return '/media/' + str(self.picture)
        else:
            return'/media/' + str(self.picture)
    def has_default_picture(self):
        if self.picture == 'tournament-pictures/default.jpg':
            return True
        return False
    def download_scraped_image(self, remove_bkg=True):
        response = requests.get('https://scratchbowling.com' + self.picture_scrape)
        original = Image.open(io.BytesIO(response.content))
        if original:
            print('opened')

            ## remove bkg from original
            if remove_bkg:
                api_key = '1ec8d33f744b07af2de3ebd0e11e21996f3b2841'
                url = 'https://sdk.photoroom.com/v1/segment'
                files = {'image_file': io.BytesIO(response.content)}
                headers = {'x-api-key': api_key}
                response = requests.post(url, files=files, headers=headers)
                response.raise_for_status()
                modified = Image.open(io.BytesIO(response.content))
            else:
                modified = original

            master = Image.new(modified.mode, modified.size)
            width, height = modified.size



            ## get bkg, resize it, and paste to master
            background = Image.open(os.path.join(settings.MEDIA_ROOT, 'tournament-pictures/background.png'))
            if height > width: resize = height
            else: resize = width
            background.thumbnail((resize, resize))
            bkg_width, bkg_height = background.size
            bkg_x = int((width - bkg_width) / 2)
            bkg_y = int((height - bkg_height) / 2)
            print('bkg_width: ' + str(bkg_width) + ' bkg_height: ' + str(bkg_height) + ' bkg_x: ' + str(bkg_x) + ' bkg_y: ' + str(bkg_y))
            master.paste(background, (bkg_x, bkg_y), background)


            master.paste(modified, (0,0), modified)
            path = 'tournament-pictures/' + str(self.tournament_id)
            xpath = os.path.join(settings.MEDIA_ROOT, path)
            if not os.path.exists(xpath):
                os.makedirs(xpath)
            master.save(xpath + '/primary.png')
            self.picture = path + '/primary.png'
            self.save()
            return self.picture


    # <editor-fold desc="-- ROSTER --">
    @property
    def roster_length(self):
        return self.tournament_datas.all().count()
    @property
    def spots_available(self):
        return self.spots_reserved - self.roster_length

    @classmethod
    def join_roster(cls, tournament_id, user_id):
        tournament = cls.get_tournament_by_uuid(tournament_id)
        if tournament and tournament.get_tournament_data(user_id) or TournamentData.create(user_id):
            return True
        return False
    @classmethod
    def leave_roster(cls, tournament_id, user_id):
        tournament = cls.get_tournament_by_uuid(tournament_id)
        if tournament:
            tournament_data = tournament.get_tournament_data(user_id)
            if tournament_data:
                return True
        return False

    def get_tournament_data(self, user_id):
        user_id = is_valid_uuid(user_id)
        if user_id:
            return self.tournament_datas.filter(user__id=user_id).first()
        return None
    # </editor-fold>



    # SCORING DATA
    def game_datas_user(self, user_id, game_number=0, amount=0):
        if game_number != 0:
            if amount != 0:
                return GameData.objects.filter(tournament_id=self.tournament_id, user_id=user_id, game_number__gte=game_number,
                                               game_number__lte=game_number + amount)
            else:
                return GameData.objects.filter(tournament_id=self.tournament_id, user_id=user_id, game_number=game_number)
        return GameData.objects.filter(tournament_id=self.tournament_id, user_id=user_id)

    def game_datas(self, game_number=0, amount=0):
        if game_number != 0:
            if amount != 0:
                return GameData.objects.filter(tournament_id=self.tournament_id, game_number__gte=game_number, game_number__lte=game_number+amount)
            else:
                return GameData.objects.filter(tournament_id=self.tournament_id, game_number=game_number)
        return GameData.objects.filter(tournament_id=self.tournament_id)

    def update_game_from_soup(self, user_id, game_number, match_number, total):
        if user_id and game_number > 0:
            game_data = GameData.objects.filter(tournament_id=self.tournament_id, user_id=user_id,
                                                game_number=game_number).first()
            if game_data:
                if game_data.total != total:
                    game_data.total = total
                    game_data.save()
                    return True
            else:
                game_data = GameData.create(self.tournament_id, user_id, game_number)
                game_data.total = total
                game_data.save()
                return True

        return False




    @property
    def scoring_data(self):
        if self.data_scoring:
            return quickle.loads(self.data_scoring)
        return []

    def get_place(self, user_id):
        user = User.get_user_by_uuid(user_id)
        if user:
            return None
        return None





    # LIVE STREAM


    ## GAMES ##

    @classmethod
    def create_game(cls, tournament_id, user_id, game_number):
        tournament_id = is_valid_uuid(tournament_id)
        user_id = is_valid_uuid(user_id)
        if tournament_id and user_id and game_number > 0:
            game_data = GameData.objects.filter(tournament_id=tournament_id, user_id=user_id, game_number=game_number).first()
            if not game_data:
                game_data = GameData.create(tournament_id, user_id, game_number)
                game_data.save()
                return True
        return False

    @classmethod
    def start_game(cls, tournament_id, user_id, game_number):
        game_data = GameData.get_game_data(tournament_id, user_id, game_number)
        if game_data and not game_data.start_time:
            game_data.start_time = datetime.now()
            return True
        return False

    @classmethod
    def get_tournament_and_user_data(cls,tournament_id, user_id):
        tournament = cls.get_tournament_by_uuid(tournament_id)
        tournament_data = None
        if tournament:
            tournament_data = tournament.get_tournament_data(user_id)
        return tournament, tournament_data


    ## TEAMS ##
    @classmethod
    def set_looking_for_team(cls, tournament_id, user_id, looking_for_team):
        tournament, tournament_data = cls.get_tournament_and_user_data(tournament_id, user_id)
        if tournament and tournament_data:
            if tournament.team_size > 0:
                if tournament_data.looking_for_team != looking_for_team:
                    tournament_data.looking_for_team = looking_for_team
                    tournament_data.save()
                return True
        return False


    @classmethod
    def leave_team(cls, tournament_id, user_id):
        tournament, user_tournament_data = cls.get_tournament_and_user_data(tournament_id, user_id)
        if tournament and user_tournament_data and user_tournament_data.team:
            if user_tournament_data.team.leave(user_tournament_data.user):
                return True
        return False




    # TAGS
    def get_tags(self):
        tags = []
        if 'Double' in self.tournament_name or 'double' in self.tournament_name:
            tags.append(1)
        if 'Sweep' in self.tournament_name or 'sweep' in self.tournament_name:
            tags.append(2)
        if 'Open' in self.tournament_name or 'open' in self.tournament_name:
            tags.append(3)
        if 'Challenge' in self.tournament_name or 'challenge' in self.tournament_name:
            tags.append(4)
        if 'Sprummer' in self.tournament_name or 'sprummer' in self.tournament_name:
            tags.append(5)
        return tags






    ## DISPLAY
    @classmethod
    def recent_display(cls):
        try:
            recent_display = cls.objects.earliest('datetime')

            return recent_display
        except cls.DoesNotExist:
            return None

    @classmethod
    def featured_live(cls):
        return cls.objects.filter(live=True).first()

    @classmethod
    def get_upcoming(cls, amount, offset=0):
        return cls.objects.filter(finished=False, live=False)[offset:offset+amount]

    @classmethod
    def get_results(cls, amount, offset=0):
        return cls.objects.filter(finished=True)[offset:offset+amount]

    @classmethod
    def get_live(cls, amount, offset=0):
        return cls.objects.filter(live=True)[offset:offset+amount]

    @classmethod
    def past_winners(cls, amount):
        users = []
        for result in cls.get_results(amount):
            winners = result.tournament_datas.filter(is_winner=True)
            if winners:
                users += winners
        return users

    @classmethod
    def completed_count(cls):
        return cls.objects.filter(finished=True).count()


class Format(models.Model):
    format_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.TextField(default='')

    is_qualifiers = models.BooleanField()
    qualifier_games = models.SmallIntegerField(default=0)
    cashers = models.SmallIntegerField(default=0)

    is_carryover = models.BooleanField(default=False)
    is_bonus_pins = models.BooleanField(default=False)


class Sponsor(models.Model):
    sponsor_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    sponsor_name =  models.CharField(max_length=60, blank=True, null=True)
    sponsor_display_name = models.CharField(max_length=60, blank=True, null=True)
    sponsor_balance = models.IntegerField(default=0, null=False, blank=True)
    sponsor_image = models.ImageField(default='sponsor-pictures/default.png', upload_to='sponsor-pictures/')

    @classmethod
    def get_sponsor(cls, uuid):
        if is_valid_uuid(uuid):
            return cls.objects.filter(sponsor_id=uuid).first()
        return None

    @classmethod
    def get_sponsor_image_uuid(cls, uuid):
        sponsor = cls.get_sponsor(uuid)
        if sponsor:
            return sponsor.get_sponsor_image()
        else:
            return '/media/sponsor-pictures/default.png'

    def get_sponsor_image(self):
        if self.sponsor_image:
            return '/media/' + self.sponsor_image.path
        else:
            return '/media/sponsor-pictures/default.png'


class Team(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='teams')
    users = models.ManyToManyField('accounts.User', related_name='teams', blank=True)

    ## m2o - tournament_datas


    def leave(self, user):
        self.users.remove(user)
        if self.users.count() == 0:
            self.delete()


class TeamInvite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='team_invites')
    sender = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='team_invites_sent')
    receiver = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='team_invites_received')
    datetime = models.DateField(default=timezone.now, editable=False)

    @classmethod
    def create(cls, tournament, send_user, receive_user):
        team_invite = cls(tournament=tournament,
                          sender=send_user,
                          receiver=receive_user)
        team_invite.save()
        return team_invite

    @classmethod
    def send_invite(cls, tournament_id, user_id, receiver_id):
        tournament, user_tournament_data = Tournament.get_tournament_and_user_data(tournament_id, user_id)
        if tournament and tournament.team_size > 0:
            receiver_tournament_data = tournament.get_tournament_data(receiver_id)
            if user_tournament_data and receiver_tournament_data:
                if not user_tournament_data.team and receiver_tournament_data.looking_for_team:
                    user = user_tournament_data.user
                    receiver = receiver_tournament_data.user

                    ## check to make sure this invite doesnt already exist
                    if tournament.team_invites.filter(sender=user, receiver=receiver).first():
                        print('User has duplicate invite, ignoring.')
                        return False

                    team_invite = cls.create(tournament, user, receiver)
                    if team_invite:
                        title = 'SBS Bowler'
                        body = user.full_name + ' sent you a team invite.'
                        data = {'invite_id': team_invite.id, 'user_id': str(user.id), 'picture': user.picture.url}

                        return True
                else:
                    print('User is already in a team')
        return False

    @classmethod
    def accept(cls, tournament_id, user_id, receiver_id):
        tournament, user_tournament_data = Tournament.get_tournament_and_user_data(tournament_id, user_id)
        if tournament and tournament.team_size > 0:
            receiver_tournament_data = tournament.get_tournament_data(receiver_id)
            if user_tournament_data and receiver_tournament_data:
                if user_tournament_data.team and receiver_tournament_data.looking_for_team:
                    ## your already in a team
                    user_tournament_data.team.leave()




                    user = user_tournament_data.user
                    receiver = receiver_tournament_data.user

                    ## check to make sure this invite doesnt already exist
                    if tournament.team_invites.filter(sender=user, receiver=receiver).first():
                        print('User has duplicate invite, ignoring.')
                        return False

                    team_invite = cls.create(tournament, user, receiver)
                    if team_invite:
                        title = 'SBS Bowler'
                        body = user.full_name + ' sent you a team invite.'
                        data = {'invite_id': team_invite.id, 'user_id': str(user.id), 'picture': user.picture.url}

                        return True
                else:
                    print('User is already in a team')
        return False



    @classmethod
    def cancel(cls, tournament_id, user_id, receiver_id):
        tournament = Tournament.get_tournament_by_uuid(tournament_id)
        if tournament:
            if tournament.team_invites.filter(Q(receiver=user_id, sender=receiver_id) | Q(receiver=receiver_id, sender=user_id)).delete():
                return True
        return False


class TournamentData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='tournament_datas')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='tournament_datas')
    team = models.ForeignKey(Team, blank=True, on_delete=models.SET_NULL, null=True, related_name='tournament_datas')
    checked_in = models.BooleanField(default=False)
    start_lane = models.SmallIntegerField(default=0)
    looking_for_team = models.BooleanField(default=False)
    is_winner = models.BooleanField(default=False)

    @classmethod
    def create(cls, tournament_id, user_id):
        tournament_data = cls(user=user_id, tournament=tournament_id)
        tournament_data.save()
        return tournament_data


class GameData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    tournament_data = models.ForeignKey(TournamentData, on_delete=models.CASCADE, related_name='game_datas')


    game_number = models.SmallIntegerField(default=0)
    match_number = models.SmallIntegerField(default=0)
    lane = models.SmallIntegerField(default=0)

    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    data_raw_scores = models.BinaryField()
    data_scores = models.BinaryField()
    bonus = models.IntegerField(default=0)
    total = models.IntegerField(default=0)



    @classmethod
    def create(cls, tournament_id, user_id, game_number):
        return cls(tournament_id=tournament_id, user_id=user_id, game_number=game_number)

    @classmethod
    def get_game_data(cls, tournament_id, user_id, game_number):
        tournament_id = is_valid_uuid(tournament_id)
        user_id = is_valid_uuid(user_id)
        if tournament_id and user_id and game_number > 0:
            return cls.filter(tournament_id=tournament_id, user_id=user_id, game_number=game_number).first()
        return None

    @property
    def scores(self):
        if self.data_scores:
            return quickle.loads(self.data_scores)
        return []
    @scores.setter
    def scores(self, score_data):
        if score_data:
            self.data_scores = quickle.dumps(score_data)

    @property
    def raw_scores(self):
        if self.data_raw_scores:
            return quickle.loads(self.data_raw_scores)
        return []
    @raw_scores.setter
    def raw_scores(self, raw_score_data):
        if raw_score_data:
            self.data_raw_scores = quickle.dumps(raw_score_data)




