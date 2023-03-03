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
            Past: '/api/past-events/',
            Future: '/api/future-events/',
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
            axios
                .get(this.eventTypes[eventType])
                .then(function (response) {
                    self.events = response.data

                    let formats = new Set(response.data.map((x) => x.format))
                    formats.forEach((fmt) => (self.showFormats[fmt] = true))

                    let organizers = new Set(
                        response.data.map((x) => x.organizer)
                    )
                    organizers.forEach(
                        (fmt) => (self.showOrganizers[fmt] = true)
                    )
                })
                .catch(function (error) {
                    // handle error
                    console.log(error)
                })
        },
    }
}
