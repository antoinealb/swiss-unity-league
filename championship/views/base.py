from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseRedirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import DeleteView

from championship.season import SEASON_LIST, find_season_by_slug


class PerSeasonView(TemplateView):
    default_season = settings.DEFAULT_SEASON
    season_list = SEASON_LIST

    def dispatch(self, request, *args, **kwargs):
        self.slug = self.kwargs.get("slug", self.default_season.slug)
        try:
            self.current_season = find_season_by_slug(self.slug)
        except KeyError:
            raise Http404(f"Unknown season {self.slug}")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        # We return two templates so that in case the season-specific one is
        # not found, the default one gets returned.
        return [
            self.template_path.format(slug=s)
            for s in (self.slug, self.default_season.slug)
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seasons"] = self.season_list
        context["current_season"] = self.current_season
        context["view_name"] = self.season_view_name
        return context


class CustomDeleteView(LoginRequiredMixin, DeleteView):
    success_message = "Successfully deleted {verbose_name}!"
    error_message = "You are not allowed to delete this {verbose_name}!"

    def allowed_to_delete(self, object, request):
        return True

    def form_valid(self, form):
        request = self.request
        verbose_name = self.object._meta.verbose_name.lower()
        if self.allowed_to_delete(self.object, request):
            messages.success(
                request, self.success_message.format(verbose_name=verbose_name)
            )
            self.delete(self.request)
        else:
            messages.error(
                request, self.error_message.format(verbose_name=verbose_name)
            )
        return HttpResponseRedirect(self.get_success_url())
