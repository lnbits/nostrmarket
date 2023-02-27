function loadTemplateAsync(path) {
  const result = new Promise(resolve => {
    const xhttp = new XMLHttpRequest()

    xhttp.onreadystatechange = function () {
      if (this.readyState == 4) {
        if (this.status == 200) resolve(this.responseText)

        if (this.status == 404) resolve(`<div>Page not found: ${path}</div>`)
      }
    }

    xhttp.open('GET', path, true)
    xhttp.send()
  })

  return result
}
