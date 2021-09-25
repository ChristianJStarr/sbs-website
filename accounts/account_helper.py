import uuid
from random import randrange

from django.contrib.auth import get_user_model

from ScratchBowling.websettings import WebSettings
from scoreboard.rank_data import deserialize_rank_data
from scoreboard.ranking_data_quick import get_top_rankings

User = get_user_model()

def get_name_from_uuid(uuid,last_name=True, bold_last=False, truncate_last=False):
    uuid = is_valid_uuid(uuid)
    if uuid is not None:
        user = User.objects.filter(user_id=uuid).first()
        if user == None:
            return 'Unknown User'

        first = str(user.first_name)
        last = str(user.last_name)
        last_initial = last[0]

        if last_name == False:
            bold_last = False

        if truncate_last:
            if bold_last:
                return first + '&nbsp;<span class="bold">' + last_initial + '.</span>'
            else:
                if last_name:
                    return first + ' ' + last_initial + '.'
                else:
                    return first
        else:
            if bold_last:
                return first + '&nbsp;<span class="bold">' + last + '</span>'
            else:
                if last_name:
                    return first + ' ' + last
                else:
                    return first
    return 'Unknown User'

def get_name_from_user(user,last_name=True, bold_last=False, truncate_last=False):
    if user == None:
        return 'Unknown User'

    first = str(user.first_name)
    last = str(user.last_name)
    last_initial = last[0]

    if last_name == False:
        bold_last = False

    if truncate_last:
        if bold_last:
            return first + '&nbsp;<span class="bold">' + last_initial + '.</span>'
        else:
            if last_name:
                return first + ' ' + last_initial + '.'
            else:
                return first
    else:
        if bold_last:
            return first + '&nbsp;<span class="bold">' + last + '</span>'
        else:
            if last_name:
                return first + ' ' + last_initial
            else:
                return first

def get_location_basic_uuid(uuid):
    uuid = is_valid_uuid(uuid)
    if uuid is not None:
        user = User.objects.filter(user_id=uuid).first()
        if user is not None:
            city = str(user.location_city)
            state = str(user.location_state)
            if city == None or city == '':
                if state == None or state == '':
                    return 'Location Unknown'
                else:
                    return state
            elif state == None or state == '':
                return city
            else:
                return city + ', ' + state

def get_location_basic_obj(user):
        if user is not None:
            city = str(user.location_city)
            state = str(user.location_state)
            if city == None or city == '':
                if state == None or state == '':
                    return 'Location Unknown'
                else:
                    return state
            elif state == None or state == '':
                return city
            else:
                return city + ', ' + state
        return 'Location Unknown'

def is_valid_uuid(val):
    try:
        return uuid.UUID(str(val))
    except ValueError:
        return None

def make_ordinal(n):
    n = int(n)
    if n == 0:
        return '0'
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    return str(n) + suffix

def display_get_bowlers(users):
    # FORMAT : Array of Lists
    # [id, name, location, rank, attend, wins, average]
    data = []
    for user in users:
        rank_data = deserialize_rank_data(user.statistics)
        if rank_data != None:
            data.append([str(user.user_id),
                         get_name_from_user(user),
                         get_location_basic_obj(user),
                         make_ordinal(rank_data.rank),
                         rank_data.attended,
                         rank_data.wins,
                         rank_data.avg_score_career
                         ])
    return data

def load_bowler_of_month():
    # FORMAT
    # [id, name, location, rank]
    websettings = WebSettings()
    if websettings.bowler_of_month != None:
        websettings.bowler_of_month = is_valid_uuid(websettings.bowler_of_month)
        user = User.objects.filter(user_id=websettings.bowler_of_month)
        if user != None:
            return [str(user.user_id), get_name_from_uuid(user.user_id), get_location_basic_uuid(user.user_id)]
    user = User.objects.all()[randrange(1, User.objects.all().count())]
    return [str(user.user_id), get_name_from_uuid(user.user_id), get_location_basic_uuid(user.user_id), get_rank_from_user(user.statistics)]

def get_rank_from_user(statistics_data, ordinal=True):
    rank = 0
    if statistics_data != None:
        rank_data = deserialize_rank_data(statistics_data)
        if rank_data != None:
            rank = rank_data.rank
    if ordinal:
        rank = make_ordinal(rank)
    return rank

def get_amount_users(include_offline=True):
    amount = 0
    if include_offline:
        amount = User.objects.all().count()
    else:
        amount = User.objects.filter(is_online=True).count()
    return amount

def get_top_ranks(amount):
    ## FORMAT
    ## [id, name, place]
    rank_datas = get_top_rankings(amount)
    data = []
    for rank_data in rank_datas:
        data.append([rank_data.user_id, get_name_from_uuid(rank_data.user_id, True, True), make_ordinal(rank_data.rank)])
    return data
