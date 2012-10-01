# Create your views here.
from django.http import HttpResponse

def profile(request):
    return HttpResponse("My profile")