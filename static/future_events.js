function events() {
    let filterList = [
        {
            title: 'Type',
            titleAll: 'All Types',
            extractProperty: (x) => x.category,
        },
        {
            title: 'Format',
            titleAll: 'All Formats',
            extractProperty: (x) => x.format,
        },
        {
            title: 'Organizer',
            titleAll: 'All Organizers',
            extractProperty: (x) => x.organizer,
        },
        {
            title: 'Region',
            titleAll: 'All Regions',
            extractProperty: (x) => x.region,
        },
    ]
    filterList = filterList.map((filter) => {
        filter.selected = {}
        return filter
    })

    return {
        events: [],
        filterList: filterList,
        shouldShow(event) {
            // Used to check if a given event should be shown. (If each of it's properties is selected)
            return this.filterList.every((filter) => {
                let property = filter.extractProperty(event)
                return filter.selected[property]
            })
        },
        currentEventType: 'Future/Past Events',
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
        toggleAll(index) {
            // If all options are selected for the filter with the given index then deselect all options. Else select all options.
            let selected = this.filterList[index].selected
            let allChecked = Object.values(selected).every(
                (value) => value === true
            )
            for (let key in selected) {
                selected[key] = !allChecked
            }
        },
        loadEvents(eventType = 'Future') {
            let self = this
            // Load the given events if they weren't loaded already.
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
            self = this
            // Set the currently shown events
            self.events = events

            // Adds for each filter the options that can be selected. Initially each option is selected.
            self.filterList.forEach((filter) => {
                let stringList = self.events.map(filter.extractProperty)
                stringList.forEach((item) => {
                    // If key isn't present, add it
                    if (!filter.selected.hasOwnProperty(item)) {
                        filter.selected[item] = true
                    }
                })
            })
        },
    }
}
