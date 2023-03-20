function events() {
    return {
        events: [],
        showFormats: {},
        showCategories: {
            // TODO: Could we fetch this dynamically as well ?
            'SUL Regular': true,
            'SUL Regional': true,
            'SUL Premier': true,
        },
        showOrganizers: {},
        currentEventType: 'Select Future or Past Events',
        eventTypes: {
            Past: {
                url: '/api/past-events/',
                data: [],
            },
            Future: {
                url: '/api/future-events/',
                data: [],
            },
        },
        allChecked(obj) {
            let res = true
            for (let val of Object.values(obj)) {
                res = res & val
            }
            return res
        },
        toggleAll(obj) {
            let newVal = !this.allChecked(obj)
            for (let key of Object.keys(obj)) {
                obj[key] = newVal
            }
        },
        loadEvents(eventType = 'Future') {
            let self = this
            if (self.eventTypes[eventType].data.length === 0) {
                axios
                    .get(self.eventTypes[eventType].url)
                    .then(function (response) {
                        self.eventTypes[eventType].data = response.data
                        self.setEvents(response.data)
                    })
                    .catch(function (error) {
                        console.log(error)
                    })
            } else {
                self.setEvents(self.eventTypes[eventType].data)
            }
        },
        setEvents(events) {
            this.events = events
            this.setFilterOptions('showFormats', (x) => x.format)
            this.setFilterOptions('showOrganizers', (x) => x.organizer)
        },
        setFilterOptions(showFilter, selectLambda) {
            self = this
            self[showFilter] = {}
            let filterOptions = new Set(self.events.map(selectLambda))
            filterOptions.forEach((option) => (self[showFilter][option] = true))
        },
    }
}
