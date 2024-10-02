const cardModal = document.getElementById('cardModal')
cardModal.addEventListener('show.bs.modal', (event) => {
    const button = event.relatedTarget
    {
        const url = button.getAttribute('data-card-image')
        const image = cardModal.querySelector('#card-img')
        image.src = url
    }
    {
        const name = button.getAttribute('data-card-name')
        const title = cardModal.querySelector('#card-title')
        title.innerHTML = name
    }
    {
        const url = button.getAttribute('data-card-url')
        const link = cardModal.querySelector('#card-link')
        link.href = url
    }
})
