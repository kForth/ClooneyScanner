import json
from os import path

import requests


class TBA:
    tba_url = 'https://thebluealliance.com/api/v3'

    def __init__(self, auth_key, use_cache=True, cache_filename="tba_cache.json"):
        self.__auth_key = auth_key
        self.__headers = {'X-TBA-Auth-Key': self.__auth_key}
        self.__use_cache = use_cache
        self.__cache_filename = cache_filename
        self._load_cache()

        self._setup_methods()

    def _load_cache(self):
        if not path.isfile(self.__cache_filename):
            json.dump({}, open(self.__cache_filename, "w+"))
        self._cache = json.load(open(self.__cache_filename))

    def _commit_cache(self):
        json.dump(self._cache, open(self.__cache_filename, "w+"))

    def _setup_methods(self):
        # TBA
        self.get_status = lambda: self._get('/status')

        # Teams
        self._get_team = lambda team, suffix='': self._get('/team/frc{0}{1}'.format(str(team), suffix))

        self.get_teams = lambda page, year='': self._get('/teams/{}'.format('/'.join([str(year), page])))
        self.get_teams_simple = lambda page, year='': self._get('/teams/{}/simple'.format('/'.join([str(year), page])))
        self.get_teams_keys = lambda page, year='': self._get('/teams/{}/keys'.format('/'.join([str(year), page])))

        self.get_team_info = lambda team: self._get_team(str(team))
        self.get_team_info_simple = lambda team: self._get_team(str(team), '/simple')

        self.get_team_years_participated = lambda team: self._get_team(str(team), '/years_participated')
        self.get_team_districts = lambda team: self._get_team(str(team), '/districts')
        self.get_team_robots = lambda team: self._get_team(str(team), '/robots')

        self.get_team_events = \
            lambda team, year='': self._get_team(str(team), '/events{0}{1}'.format('/' if year else'', year))
        self.get_team_events_simple = \
            lambda team, year='': self._get_team(str(team), '/events{0}{1}/simple'.format('/' if year else'', year))
        self.get_team_events_keys = \
            lambda team, year='': self._get_team(str(team), '/events{0}{1}/keys'.format('/' if year else'', year))

        self.get_team_event_matches = \
            lambda team, event_id: self._get_team(str(team), '/event/{}/matches'.format(event_id))
        self.get_team_event_matches_simple = \
            lambda team, event_id: self._get_team(str(team), '/event/{}/matches/simple'.format(event_id))
        self.get_team_event_matches_keys = \
            lambda team, event_id: self._get_team(str(team), '/event/{}/matches/keys'.format(event_id))

        self.get_team_event_awards = \
            lambda team, event_id: self._get_team(str(team), '/event/{}/awards'.format(event_id))
        self.get_team_event_status = \
            lambda team, event_id: self._get_team(str(team), '/event/{}/status'.format(event_id))

        self.get_team_awards = \
            lambda team, year='': self._get_team(str(team), '/awards{0}{1}'.format('/' if year else '', year))

        self.get_team_matches = lambda team, year: self._get_team(str(team), '/matches/{0}'.format(str(year)))
        self.get_team_matches_simple = \
            lambda team, year: self._get_team(str(team), '/matches/{}/simple'.format(str(year)))
        self.get_team_matches_keys = lambda team, year: self._get_team(str(team), '/matches/{}/keys'.format(str(year)))

        self.get_team_media = lambda team, year: self._get_team(str(team), '/media/{}'.format(str(year)))
        self.get_team_social_media = lambda team: self._get_team(str(team), '/social_media')

        # Events
        self._get_event = lambda event_id, suffix='': self._get('/event/{0}{1}'.format(event_id, suffix))

        self.get_events = lambda year: self._get('/events/{}'.format(str(year)))
        self.get_events_simple = lambda year: self._get('/events/{}/simple'.format(str(year)))
        self.get_events_keys = lambda year: self._get('/events/{}/keys'.format(str(year)))

        self.get_event_info = lambda event_id: self._get_event(event_id)
        self.get_event_info_simple = lambda event_id: self._get_event(event_id, '/simple')

        self.get_event_alliances = lambda event_id: self._get_event(event_id, '/alliances')
        self.get_event_insights = lambda event_id: self._get_event(event_id, '/insights')
        self.get_event_oprs = lambda event_id: self._get_event(event_id, '/oprs')
        self.get_event_predictions = lambda event_id: self._get_event(event_id, '/predictions')
        self.get_event_rankings = lambda event_id: self._get_event(event_id, '/rankings')
        self.get_event_district_points = lambda event_id: self._get_event(event_id, '/district_points')
        self.get_event_awards = lambda event_id: self._get_event(event_id, '/awards')

        self.get_event_teams = lambda event_id: self._get_event(event_id, '/teams')
        self.get_event_teams_simple = lambda event_id: self._get_event(event_id, '/teams/simple')
        self.get_event_teams_keys = lambda event_id: self._get_event(event_id, '/teams/keys')

        self.get_event_matches = lambda event_id: self._get_event(event_id, '/matches')
        self.get_event_matches_simple = lambda event_id: self._get_event(event_id, '/matches/simple')
        self.get_event_matches_keys = lambda event_id: self._get_event(event_id, '/matches/keys')

        # Match
        self.get_match_info = lambda match_key: self._get('/match/' + match_key)
        self.get_match_info_simple = lambda match_key: self._get('/match/' + match_key)

        # District
        self._get_district = lambda id, suffix: self._get('/districts/{0}{1}'.format(id, suffix))

        self.get_districts = lambda year: self._get('/districts/{}'.format(str(year)))

        self.get_district_events = lambda district_id: self._get_district(district_id, '/events')
        self.get_district_events_simple = lambda district_id: self._get_district(district_id, '/events/simple')
        self.get_district_events_keys = lambda district_id: self._get_district(district_id, '/events/keys')

        self.get_district_teams = lambda district_id: self._get_district(district_id, '/teams')
        self.get_district_teams_simple = lambda district_id: self._get_district(district_id, '/teams/simple')
        self.get_district_teams_keys = lambda district_id: self._get_district(district_id, '/teams/keys')

        self.get_district_rankings = lambda district_id: self._get_district(district_id, '/rankings')

    def _get(self, url):
        headers = dict(self.__headers)
        if self.__use_cache and url in list(self._cache.keys()):
            headers['If-Modified-Since'] = self._cache[url]['date']
        result = requests.get(self.tba_url + url, headers=headers)
        if result.status_code == 200:
            if self.__use_cache:
                self._cache[url] = {'date': result.headers['Last-Modified'], 'json': result.json()}
                self._commit_cache()
            return result.json()
        elif result.status_code == 304:
            if self.__use_cache and url in self._cache.keys():
                    return self._cache[url]['json']
            else:
                raise NotModifiedException('Url ({0}) not modified since: {1}'.format(url, result.headers['Last-Modified']))
        else:
            raise BadResponseCodeException('Url ({0}) had bad Response Code: {1}'.format(url, result.status_code))


class NotModifiedException(Exception):
    pass


class BadResponseCodeException(Exception):
    pass