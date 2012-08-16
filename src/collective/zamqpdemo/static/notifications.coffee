jQuery ($) ->
  # Stomp.js boilerplate
  Stomp.WebSocketClass = SockJS

  # Create new Stomp client
  client = Stomp.client "http://" + window.location.hostname + ":55674/stomp"

  # Declare subscriptions and handlers for them
  on_connect = (response) ->
    console?.log "on_connect #{response}"
    id = client.subscribe "/exchange/amqpdemo.notifications/*", (message) ->
      console?.log "on_message #{message}"
      data = $.parseJSON(message.body)
      el = $("<p class=\"amqp-notification\">Just published:<br/>" \
             + "<a href=\"#{data.url}\">#{data.title}</a></p>")
      window.setTimeout (-> el.fadeOut 500), 3000
      $("body").append el

  # Log any errors
  on_error = (response) ->
    console?.log "on_error #{response}"

  # Connect!
  client.connect "amqpdemo", "amqpdemo", on_connect, on_error, "/amqpdemo"
