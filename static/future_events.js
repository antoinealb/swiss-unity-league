function events() {
    return {
        events: [],
        showFormats: {
            // TODO: Could we fetch this dynamically as well ?
            Standard: true,
            Modern: true,
            Legacy: true,
            Pioneer: true,
            Limited: true,
        },
        showCategories: {
            // TODO: Could we fetch this dynamically as well ?
            'SUL Regular': true,
            'SUL Regional': true,
            'SUL Premier': true,
        },
        allFormatsStatus() {
            let res = true
            for (let val of Object.values(this.showFormats)) {
                res = res & val
            }
            return res
        },
        allCategoriesStatus() {
            let res = true
            for (let val of Object.values(this.showCategories)) {
                res = res & val
            }
            return res
        },
        toggleAllFormats() {
            let newVal = !this.allFormatsStatus()
            for (let key of Object.keys(this.showFormats)) {
                this.showFormats[key] = newVal
            }
        },
        toggleAllCategories() {
            let newVal = !this.allCategoriesStatus()
            for (let key of Object.keys(this.showCategories)) {
                this.showCategories[key] = newVal
            }
        },
        loadEvents() {
            let self = this
            axios
                .get('/api/future-events/')
                .then(function (response) {
                    self.events = response.data
                })
                .catch(function (error) {
                    // handle error
                    console.log(error)
                })
        },
    }
}
