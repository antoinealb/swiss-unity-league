function events(seasonUrls) {
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

    eventsPerSeason = {}
    seasonUrls.forEach((item) => {
        const seasonName = Object.keys(item)[0]
        eventsPerSeason[seasonName] = {
            url: item[seasonName],
            data: [],
        }
    })

    return {
        events: [],
        filterList: filterList,
        shouldShow(event) {
            // Used to check if a given event should be shown. (If each of it's properties is selected)
            return this.filterList.every((filter) => {
                let property = filter.extractProperty(event)
                return (
                    filter.selected[property] ||
                    Object.values(filter.selected).every(
                        (value) => value === false
                    )
                )
            })
        },
        eventsPerSeason: eventsPerSeason,
        currentSeason: Object.keys(eventsPerSeason)[0],
        toggleAll(index) {
            // If all options are selected for the filter with the given index then deselect all options. Else select all options.
            let selected = this.filterList[index].selected
            for (let key in selected) {
                selected[key] = false
            }
        },
        async loadEvents(seasonName) {
            let self = this

            // Fast path: if we request the upcoming events, load them from the
            // DOM where Django will have put them.
            if (!seasonName) {
                seasonName = self.currentSeason
                const events = JSON.parse(
                    document.getElementById('events-data').textContent
                )
                self.eventsPerSeason[seasonName].data = events
                self.setEvents(self.eventsPerSeason[seasonName].data)
                return
            }

            // Slow path, cached: Simply set the events from the cache
            if (self.eventsPerSeason[seasonName].data.length > 0) {
                self.setEvents(self.eventsPerSeason[seasonName].data)
                return
            }

            // Slow path, not in the cache: issue an API call to fetch events
            // for the given season.
            response = await axios.get(self.eventsPerSeason[seasonName].url)
            self.eventsPerSeason[seasonName].data = response.data
            self.setEvents(response.data)
        },
        setEvents(events) {
            self = this
            // Set the currently shown events
            self.events = events

            self.filterList.forEach((filter) => {
                let stringList = self.events.map(filter.extractProperty)
                stringList.forEach((item) => {
                    // If key isn't present, add it
                    if (!filter.selected.hasOwnProperty(item)) {
                        filter.selected[item] = false
                    }
                })
                // Sort keys alphabetically, ignoring case, and create a new sorted object
                const sortedKeys = Object.keys(filter.selected).sort((a, b) =>
                    a.toLowerCase().localeCompare(b.toLowerCase())
                )
                const sortedSelected = {}
                sortedKeys.forEach((key) => {
                    sortedSelected[key] = filter.selected[key]
                })
                filter.selected = sortedSelected
            })
        },
    }
}
