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
        allChecked(obj){
            let res = true
            for (let val of Object.values(obj)) {
                res = res & val
            }
            return res
        },
        toggleAll(obj){
            let newVal = !this.allChecked(obj)
            for (let key of Object.keys(obj)) {
                obj[key] = newVal
            }
        },
        loadEvents() {
            let self = this
            axios
                .get('/api/future-events/')
                .then(function (response) {
                    self.events = response.data
                    let uniqueFormats = [... new Set(response.data.map(x => x.format))]
                    for (let format of uniqueFormats) {
                        self.showFormats[format] = true
                    }
                    let uniqueOrganizers = [... new Set(response.data.map(x => x.organizer))]
                    for (let organizer of uniqueOrganizers) {
                        self.showOrganizers[organizer] = true
                    }                    
                })
                .catch(function (error) {
                    // handle error
                    console.log(error)
                })
        },
    }
}
