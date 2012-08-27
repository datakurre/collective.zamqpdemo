jQuery ($) ->

  # Define helper for getting the member exchange cookie
  getMemberExchange = ->
    key = "exchange="
    for c in document.cookie.split(";")
      c = c.substring(1, c.length) while c.charAt(0) is " "
      return c.substring(key.length, c.length) if c.indexOf(key) == 0
    return null

  # Define helper for setting the member exchange cookie
  setMemberExchange = (value) ->
    date = new Date()
    date.setTime(date.getTime() + (24 * 60 * 60 * 1000))
    expires = "; expires=" + date.toGMTString()
    document.cookie = "exchange=" + value + expires + "; path=/"

  # Define helper method to add new notification
  addNotification = (html) ->
    container = $("#amqp-notifications")
    if not container.length
      container = $("<div id=\"amqp-notifications\"></div>").appendTo("body")
    notification = $("<div class=\"amqp-notification\">#{html}</div>")
    window.setTimeout (-> notification.fadeOut 500, \
                       -> do notification.remove), 5000
    notification.appendTo container

  # Configure Stomp to use SockJS
  Stomp.WebSocketClass = SockJS

  # Create new Stomp client
  client = Stomp.client "http://" + window.location.hostname + ":55674/stomp"

  # Test if we are authenticated or not
  authenticated = not $("#personaltools-login").length
  member_exchange = do getMemberExchange

  #
  # Handle connections and errors
  #

  on_connect_guest = (response) ->
    console?.log "on_connect #{response}"

    # Subscribe publication messages
    client.subscribe "/topic/published", (message) ->
      console?.log "on_message #{message}"
      data = JSON.parse(message.body)
      addNotification "<p>Just published:<br/>" \
                      + "<a href=\"#{data.url}\">#{data.title}</a></p>"

  on_error_guest = (response) ->
    console?.log "on_error #{response}"


  on_connect_member = (response) ->
    # console?.log "on_connect #{response}"
    on_connect_guest response

    # Subscribe private messages
    client.subscribe "/exchange/#{member_exchange}/*", (message) ->
      console?.log "on_message #{message}"
      # deserialize
      if message.headers["content-type"] == "application/x-json"
        data = JSON.parse(message.body)

        if /^\/exchange\/reviewers\//.test message.destination
          actions = $("<ul></ul>")
          for key, value of data?.actions
            actions.append "<li><a href=\"#{data.url}/content_status_modify?" \
                            + "workflow_action=#{key}\">#{value}</a></li>"
          if actions.children().length
            actions = "<ul>#{actions.html()}</ul>"
          else
            actions = ""
          addNotification("<p>Waiting for review:<br/>" \
                          + "<a href=\"#{data.url}\">#{data.title}</a></p>" \
                          + actions)
      else
        addNotification message.body

    # Subscribe keepalive-queue to keep the member exchange alive
    client.subscribe "/amq/queue/#{member_exchange}-keepalive", (message) ->
      null

  on_error_member = (response) ->
    console?.log "on_error #{response}"
    if new RegExp("no exchange '#{member_exchange}'").test response
      console?.log "DO AUTHENTICATE"
      do authenticate


  on_connect_auth = (response) ->
    console?.log "on_connect #{response}"
    console?.log "sending authentication request"

    $.get "#{portal_url}/@@configure-member-exchange", (response) ->
      member_exchange = JSON.parse(response)
      if member_exchange
        setMemberExchange(member_exchange)
        on_connect_member "AUTHENTICATED"
      else
        on_connect_guest "AUTHENTICATION REJECTED"

  on_error_auth = (response) ->
    console?.log "on_error #{response}"
    do connect_guest


  connect_guest = ->
    client.connect "guest", "guest", on_connect_guest, on_error_guest, "/"

  connect_member = ->
    client.connect "guest", "guest", on_connect_member, on_error_member, "/"

  authenticate = ->
    client.connect "guest", "guest", on_connect_auth, on_error_auth, "/"

  # XXX: ^ To make the above connection safe, you must create a new (untrusted)
  # user on RabbitMQ with permissions similar to
  # Configure     Write         Read
  # 'amq.gen-.*', 'amq.gen-.*', 'amq.gen-.*|member-.*|amq.topic'
  # and update credentials above to connect as that user.

  if not authenticated
    console?.log "CONNECT GUEST"
    do connect_guest
  else if not member_exchange
    do authenticate
  else
    console?.log "CONNECT MEMBER"
    do connect_member
