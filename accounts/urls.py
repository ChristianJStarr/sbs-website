from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView

from . import views
from . import data

app_name = 'accounts'

urlpatterns = [
    path('view/<id>/', views.accounts_account_view, name='profile'),
    path('view/add/<id>', views.accounts_add_view, name='add'),
    path('view/remove/<id>', views.accounts_remove_view, name='remove'),

    path('claim/<id>', views.accounts_claim_view, name='claim'),

    path('data/profile-pic/<id>', data.get_profile_pic, name='data-profile-pic'),

    path('login/', views.accounts_login_view, name='login'),
    path('signup/', views.accounts_signup_view, name='signup'),
    path('logout/', views.accounts_logout_view, name='logout'),
    path('modify/', views.accounts_modify_view, name='modify'),
    path('activate/<slug:uidb64>/<slug:token>/', views.activate, name='activate'),


    path('scraper/', views.start_master_scraper, name='scraper'),
    path('scraperlog/', views.accounts_scraper_view, name='scraperlog'),
    path('socialcard/image/<id>/', views.accounts_socialcard_image, name='socialcard-image'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)