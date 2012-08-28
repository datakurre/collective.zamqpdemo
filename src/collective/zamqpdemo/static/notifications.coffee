jQuery ($) ->
  # This script opens a SockJS-connection to defined RabbitMQ broker,
  # subscribes to certain queues using web-stomp and displays notifications
  # from received messages.

  # At first, we define helper methods for setting, reading and clearing
  # our member exchange cookie. We want to disturb Plone as little as possible
  # and always try to connect the last known working member exchange before
  # asking Plone to create a new one.

  setMemberExchange = (value) ->
    date = new Date()
    date.setTime(date.getTime() + (24 * 60 * 60 * 1000))
    expires = "; expires=" + date.toGMTString()
    document.cookie = "exchange=" + value + expires + "; path=/"

  getMemberExchange = ->
    key = "exchange="
    for c in document.cookie.split(";")
      c = c.substring(1, c.length) while c.charAt(0) is " "
      return c.substring(key.length, c.length) if c.indexOf(key) == 0
    return null

  clearMemberExchange = ->
    date = new Date()
    date.setTime(date.getTime() - (24 * 60 * 60 * 1000))
    expires = "; expires=" + date.toGMTString()
    document.cookie = "exchange=" + expires + "; path=/"


  # Then we define a helper method for creating dom element for notifications.
  # This simply takes some html, wraps within a notification elements and
  # appends it to dom with timouting fadout.

  addNotification = (html) ->
    container = $("#amqp-notifications")
    if not container.length
      container = $("<div id=\"amqp-notifications\"></div>").appendTo("body")
    notification = $("<div class=\"amqp-notification\">#{html}</div>")
    window.setTimeout (-> notification.fadeOut 500, \
                       -> do notification.remove), 5000
    notification.appendTo container


  # Next we define connection handlers for anonymous connections

  on_connect_guest = (response) ->
    console?.log "on_connect #{response}"

    # We subscibe publication notifications, deserialize and display them
    client.subscribe "/topic/published", (message) ->
      console?.log "on_message #{message}"
      data = JSON.parse(message.body)
      addNotification "<p>Just published:<br/>" \
                      + "<a href=\"#{data.url}\">#{data.title}</a></p>"

  on_error_guest = (response) ->
    console?.log "on_error #{response}"


  # Then we define connection handlers for authenticated connections

  on_connect_member = (response) ->
    # At first, we subscribe the same queues as anonymous users
    on_connect_guest response

    # Then we subscribe to member exchange and may support different types of
    # notifications from different sources
    client.subscribe "/exchange/#{member_exchange}/*", (message) ->
      console?.log "on_message #{message}"

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

    # Finally, we subscribe keepalive-queue to keep the member exchange alive
    client.subscribe "/amq/queue/#{member_exchange}-keepalive", (message) ->
      null

  # If member exchange subscription fails, we must re-authenticate, thus
  # ask Plone to declare new exchange for us.
  on_error_member = (response) ->
    console?.log "on_error #{response}"
    if new RegExp("no exchange '#{member_exchange}'").test response
      console?.log "DO AUTHENTICATE"
      do authenticate


  # Then we define connection handlers, when we need to authenticate, thus ask
  # Plone to define new exchange for us (or fallback to public queues only)

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


  # Finally, we define all different connection types

  connect_guest = ->
    client.connect "guest", "guest", on_connect_guest, on_error_guest, "/"

  connect_member = ->
    client.connect "guest", "guest", on_connect_member, on_error_member, "/"

  authenticate = ->
    client.connect "guest", "guest", on_connect_auth, on_error_auth, "/"

  # XXX: To make the above connections safe, you must create a new (untrusted)
  # user on RabbitMQ with permissions similar to
  # Configure     Write         Read
  # 'amq.gen-.*', 'amq.gen-.*', 'amq.gen-.*|member-.*|amq.topic'
  # and update credentials above to connect as that user.


  # Now everything is defined and we are ready for action:
  #
  # 1) Let's configure our stomp library to use SockJS
  Stomp.WebSocketClass = SockJS

  # 2) And create a new stomp client ready to open a connction
  client = Stomp.client "http://" + window.location.hostname + ":55674/stomp"

  # 3) Find out, if we should be authenticated or not
  authenticated = not $("#personaltools-login").length

  # 4) Read the member exchange cookie, if it exists
  member_exchange = do getMemberExchange

  # 5) Connect!
  if not authenticated
    console?.log "CONNECT GUEST"
    do connect_guest
    do clearMemberExchange
  else if not member_exchange
    do authenticate
  else
    console?.log "CONNECT MEMBER"
    do connect_member
