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

function imgSizeFit(img, maxWidth = 1024, maxHeight = 768) {
  let ratio = Math.min(
    1,
    maxWidth / img.naturalWidth,
    maxHeight / img.naturalHeight
  )
  return { width: img.naturalWidth * ratio, height: img.naturalHeight * ratio }
}

async function hash(string) {
  const utf8 = new TextEncoder().encode(string)
  const hashBuffer = await crypto.subtle.digest('SHA-256', utf8)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashHex = hashArray
    .map(bytes => bytes.toString(16).padStart(2, '0'))
    .join('')
  return hashHex
}

function isJson(str) {
  if (typeof str !== 'string') {
    return false
  }
  try {
    JSON.parse(str)
    return true
  } catch (error) {
    return false
  }
}

function satOrBtc(val, showUnit = true, showSats = false) {
  const value = showSats
    ? LNbits.utils.formatSat(val)
    : val == 0
      ? 0.0
      : (val / 100000000).toFixed(8)
  if (!showUnit) return value
  return showSats ? value + ' sat' : value + ' BTC'
}

function timeFromNow(time) {
  // Get timestamps
  let unixTime = new Date(time).getTime()
  if (!unixTime) return
  let now = new Date().getTime()

  // Calculate difference
  let difference = unixTime / 1000 - now / 1000

  // Setup return object
  let tfn = {}

  // Check if time is in the past, present, or future
  tfn.when = 'now'
  if (difference > 0) {
    tfn.when = 'future'
  } else if (difference < -1) {
    tfn.when = 'past'
  }

  // Convert difference to absolute
  difference = Math.abs(difference)

  // Calculate time unit
  if (difference / (60 * 60 * 24 * 365) > 1) {
    // Years
    tfn.unitOfTime = 'years'
    tfn.time = Math.floor(difference / (60 * 60 * 24 * 365))
  } else if (difference / (60 * 60 * 24 * 45) > 1) {
    // Months
    tfn.unitOfTime = 'months'
    tfn.time = Math.floor(difference / (60 * 60 * 24 * 45))
  } else if (difference / (60 * 60 * 24) > 1) {
    // Days
    tfn.unitOfTime = 'days'
    tfn.time = Math.floor(difference / (60 * 60 * 24))
  } else if (difference / (60 * 60) > 1) {
    // Hours
    tfn.unitOfTime = 'hours'
    tfn.time = Math.floor(difference / (60 * 60))
  } else if (difference / 60 > 1) {
    // Minutes
    tfn.unitOfTime = 'minutes'
    tfn.time = Math.floor(difference / 60)
  } else {
    // Seconds
    tfn.unitOfTime = 'seconds'
    tfn.time = Math.floor(difference)
  }

  // Return time from now data
  return `${tfn.time} ${tfn.unitOfTime}`
}

function isValidImageUrl(string) {
  let url
  try {
    url = new URL(string)
  } catch (_) {
    return false
  }
  return url.protocol === 'http:' || url.protocol === 'https:'
}

function isValidKey(key, prefix = 'n') {
  try {
    if (key && key.startsWith(prefix)) {
      let { _, data } = NostrTools.nip19.decode(key)
      key = data
    }
    return isValidKeyHex(key)
  } catch (error) {
    return false
  }
}

function isValidKeyHex(key) {
  return key?.toLowerCase()?.match(/^[0-9a-f]{64}$/)
}

function formatCurrency(value, currency) {
  return new Intl.NumberFormat(window.LOCALE, {
    style: 'currency',
    currency: currency
  }).format(value)
}