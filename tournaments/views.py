from datetime import datetime
from uuid import UUID
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.template.defaulttags import register
from ScratchBowling.forms import TournamentsSearch
from ScratchBowling.pages import create_page_obj
from accounts.account_helper import get_location_basic_uuid, is_valid_uuid
from centers.models import Center
from accounts.forms import User
from oils.oil_pattern import  get_oil_display_data
from tournaments.forms import CreateTournament, ModifyTournament
from tournaments.models import Tournament
from oils.oil_pattern_scraper import get_oil_colors
from tournaments.tournament_utils import make_ordinal, get_average, get_bowler_id_from_place


@register.filter
def get_center_data(value):
    if validate_uuid4(value):
        center = get_object_or_404(Center, center_id=value)
        if center is not None:
            centers_string = center.location_city + center.location_state
            return centers_string

@register.filter
def placer(value):
    return value.text

@register.filter
def get_bowler_from_place(tournament_id, place):
    return get_bowler_id_from_place(tournament_id, place)

@register.filter
def getaverage(user_id, tournament_id):
    return get_average(tournament_id, user_id)


@register.filter
def bowler_name(uuid, bold_last=False):
    uuid = is_valid_uuid(uuid)
    if uuid is not None:
        name = User.objects.filter(user_id=uuid).first()
        if name == None:
            return 'Unknown Name'
        truncate = False
        if truncate is True:
            if bold_last is True:
                return name.first_name + '&nbsp;<span class="bold">' + name.last_name[0] + '.</span>'
            else:
                return name.first_name + ' ' + name.last_name[0] + '.'
        else:
            if bold_last is True:
                return name.first_name + '&nbsp;<span class="bold">' + name.last_name + '</span>'
            else:
                return name.first_name + ' ' + name.last_name

@register.filter
def bowler_location(uuid):
    return get_location_basic_uuid(uuid)

@register.filter
def tournament_date(tournament_id):
    tournament_id = is_valid_uuid(tournament_id)
    if tournament_id is not None:
        tournament = Tournament.objects.filter(tournament_id=tournament_id).first()
        if tournament is not None:
            return tournament.tournament_date

@register.filter
def tournament_name(tournament_id):
    tournament_id = is_valid_uuid(tournament_id)
    if tournament_id is not None:
        tournament = Tournament.objects.filter(tournament_id=tournament_id).first()
        if tournament is not None:
            return tournament.tournament_name

@register.filter
def ordinal(value):
    return make_ordinal(value)

@register.filter
def center_name(uuid):
    uuid = is_valid_uuid(uuid)
    if uuid is not None:
        center = Center.objects.filter(center_id=uuid).first()
        if center != None and center.center_name != None:
            return center.center_name

@register.filter
def center_location(uuid):
    uuid = is_valid_uuid(uuid)
    if uuid is not None:
        center = Center.objects.filter(center_id=uuid).first()
        city = str(center.location_city)
        state = str(center.location_state)
        if city == None or city == '':
            if state == None or state == '':
                return 'Location Unknown'
            else:
                return state
        elif state == None or state == '':
            return city
        else:
            return city + ', ' + state



def tournaments_results_views(request, page=1, search=''):
    page = int(page)
    per_page = 20
    selected_upcoming = False
    tournaments_count = Tournament.objects.all().count()
    tournaments_past = Tournament.objects.filter(tournament_date__lte=datetime.now().date()).exclude(tournament_date=datetime.now().date(), tournament_time__gt=datetime.now().time())

    if request.method == 'POST':
        form = TournamentsSearch(request.POST)
        if form.is_valid():
            search = form.cleaned_data['search_args']
            tournaments_past = tournaments_past.filter(Q(tournament_name__icontains=search) | Q(tournament_date__icontains=search))
    elif search != '':
        tournaments_past = tournaments_past.filter(Q(tournament_name__icontains=search) | Q(tournament_date__icontains=search))

    reallist = []
    for tournament in tournaments_past:

        qualifying = None ##get_qualifying_object(tournament)
        if qualifying != None and len(qualifying) > 0:
            reallist.append(tournament)
    start = (per_page * page) - per_page
    end = per_page * page
    total_count = len(reallist)
    tournaments_past = reallist[start:end]
    return render(request, 'tournaments/main-tournaments.html', {'nbar': 'tournaments',
                                                                 'tournaments_past': tournaments_past,
                                                                 'selected_upcoming':selected_upcoming,
                                                                 'tournaments_count': tournaments_count,
                                                                 'upcoming_count': Tournament.objects.filter(tournament_date__gte=datetime.now().date()).exclude(tournament_date=datetime.now().date(), tournament_time__lt=datetime.now().time()).count(),
                                                                 'results_count': total_count,
                                                                 'search_type': 'tournaments_results',
                                                                 'search': search,
                                                                 'page': create_page_obj(page, per_page, total_count),
                                                                 'page_title': 'Tournament Results',
                                                                 'page_description': 'Check our list of Tournament Results and view info about a Tournament.',
                                                                 'page_keywords': 'Tournament, Results, Scores, Information, Statistics, Bowlers, Checking, Reserve, Roster, Bowl, Entry'
                                                                 })


def tournaments_upcoming_views(request):
    selected_upcoming = True
    tournaments_count = Tournament.objects.all().count()
    tournaments_upcoming = Tournament.objects.filter(tournament_date__gte=datetime.now().date()).exclude(tournament_date=datetime.now().date(), tournament_time__lt=datetime.now().time())
    return render(request, 'tournaments/main-tournaments.html', {'nbar': 'tournaments',
                                                                 'tournaments_upcoming': tournaments_upcoming,
                                                                 'selected_upcoming':selected_upcoming,
                                                                 'upcoming_count': tournaments_upcoming.count(),
                                                                 'tournaments_count': tournaments_count,
                                                                 'search_type': 'tournaments_upcoming',
                                                                 'page_title': 'Upcoming Tournaments',
                                                                 'page_description': 'View all of our Upcoming Tournaments. Join a Roster. Bowl Today!',
                                                                 'page_keywords': 'Bowl, Upcoming, Tournaments, Roster, Join, View, Reserver, Entry, Results, Scores'

                                                                 })


def tournaments_view_views(request, id):
    tournament = Tournament.objects.get(tournament_id=id)

    oil_pattern = get_oil_display_data(879)
    oil_colors = get_oil_colors()

    return render(request, 'tournaments/view-tournament.html', {'nbar': 'tournaments', 'tournament': tournament, 'oil_pattern': oil_pattern, 'oil_colors': oil_colors})


def tournaments_modify_views(request, id):
    if request.user.admin is True and validate_uuid4(id) is True:
        tournament = get_object_or_404(Tournament, tournament_id=id)
        if tournament is None:
            redirect('/')
        if request.method == 'POST':
            form = ModifyTournament(request.POST)
            if form.is_valid():
                testform = None

                tournament.tournament_name = form.cleaned_data.get('tournament_name')
                tournament.tournament_description = form.cleaned_data.get('tournament_description')
                tournament.entry_fee = form.cleaned_data.get('entry_fee')
                tournament.total_games = form.cleaned_data.get('total_games')
                tournament.tournament_date = form.cleaned_data.get('tournament_date')
                tournament.tournament_time = form.cleaned_data.get('tournament_time')
                tournament.sponsor_image = '/media/sponsors/sponsor-image-03.png'
                tournament.save(force_update=True)
                if tournament.tournament_id != id:
                    return redirect('/')
                return redirect('/tournaments/')
        else:
            testform = None
            form = ModifyTournament(initial={'tournament_name': tournament.tournament_name,'tournament_description': tournament.tournament_description,'entry_fee': tournament.entry_fee,'total_games': tournament.total_games, 'tournament_date': tournament.tournament_date.strftime('%d-%m-%Y'), 'tournament_time': tournament.tournament_time})
        return render(request, 'tournaments/modify-tournament.html', {'nbar': 'tournaments', 'form': form, 'tournament': tournament, 'testform':testform})
    else:
        return redirect('/')


def validate_uuid4(uuid_string):

    try:
        val = UUID(uuid_string, version=4)
    except ValueError:
        # If it's a value error, then the string
        # is not a valid hex code for a UUID.
        return False

    return True


def tournaments_create_views(request):
    if request.method == 'POST':
        form = CreateTournament(request.POST)
        if form.is_valid():
            tournament = Tournament.objects.create()
            tournament.tournament_name = form.cleaned_data.get('tournament_name')
            tournament.tournament_description = form.cleaned_data.get('tournament_description')
            tournament.tournament_date = form.cleaned_data.get('tournament_date')
            tournament.tournament_time = form.cleaned_data.get('tournament_time')
            tournament.save()
            return redirect('/tournaments/view/' + str(tournament.tournament_id))
    else:
        form = CreateTournament()

    return render(request, 'tournaments/create-tournament.html', {'form': form, 'nbar': 'tournaments'})


def get_date_time(date, time):
    if date is not None and time is not None:
        date_str = date + ' ' + time
        return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    else:
        return datetime.now()

















