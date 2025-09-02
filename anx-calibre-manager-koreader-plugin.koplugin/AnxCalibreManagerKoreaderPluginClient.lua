local UIManager = require("ui/uimanager")
local logger = require("logger")
local socketutil = require("socketutil")

-- Push/Pull - 增加timeout时间以适应远程服务器
local PROGRESS_TIMEOUTS = { 7, 10 }
-- Login/Register
local AUTH_TIMEOUTS     = { 7, 10 }

local AnxCalibreManagerKoreaderPluginClient = {
    service_spec = nil,
    custom_url = nil,
}

function AnxCalibreManagerKoreaderPluginClient:new(o)
    if o == nil then o = {} end
    setmetatable(o, self)
    self.__index = self
    if o.init then o:init() end
    return o
end

function AnxCalibreManagerKoreaderPluginClient:init()
    local Spore = require("Spore")
    self.client = Spore.new_from_spec(self.service_spec, {
        base_url = self.custom_url,
    })
    package.loaded["Spore.Middleware.GinClient"] = {}
    require("Spore.Middleware.GinClient").call = function(_, req)
        req.headers["accept"] = "application/vnd.koreader.v1+json"
    end
    package.loaded["Spore.Middleware.KOSyncAuth"] = {}
    require("Spore.Middleware.KOSyncAuth").call = function(args, req)
        req.headers["x-auth-user"] = args.username
        req.headers["x-auth-key"] = args.userkey
    end
    package.loaded["Spore.Middleware.AsyncHTTP"] = {}
    require("Spore.Middleware.AsyncHTTP").call = function(args, req)
        -- disable async http if Turbo looper is missing
        if not UIManager.looper then return end
        req:finalize()
        local result
        require("httpclient"):new():request({
            url = req.url,
            method = req.method,
            body = req.env.spore.payload,
            on_headers = function(headers)
                for header, value in pairs(req.headers) do
                    if type(header) == "string" then
                        headers:add(header, value)
                    end
                end
            end,
        }, function(res)
            result = res
            -- Turbo HTTP client uses code instead of status
            -- change to status so that Spore can understand
            result.status = res.code
            coroutine.resume(args.thread)
        end)
        return coroutine.create(function() coroutine.yield(result) end)
    end
end



function AnxCalibreManagerKoreaderPluginClient:authorize(username, password)
    self.client:reset_middlewares()
    self.client:enable("Format.JSON")
    self.client:enable("GinClient")
    self.client:enable("KOSyncAuth", {
        username = username,
        userkey = password,
    })
    socketutil:set_timeout(AUTH_TIMEOUTS[1], AUTH_TIMEOUTS[2])
    local ok, res = pcall(function()
        return self.client:authorize()
    end)
    socketutil:reset_timeout()
    if ok then
        return res.status == 200, res.body
    else
        logger.dbg("AnxCalibreManagerKoreaderPluginClient:authorize failure:", res)
        return false, res.body
    end
end

function AnxCalibreManagerKoreaderPluginClient:update_progress(
        username,
        password,
        document,
        progress,
        percentage,
        device,
        device_id,
        callback)
    self.client:reset_middlewares()
    self.client:enable("Format.JSON")
    self.client:enable("GinClient")
    self.client:enable("KOSyncAuth", {
        username = username,
        userkey = password,
    })
    -- Set *very* tight timeouts to avoid blocking for too long...
    socketutil:set_timeout(PROGRESS_TIMEOUTS[1], PROGRESS_TIMEOUTS[2])
    local co = coroutine.create(function()
        local ok, res = pcall(function()
            return self.client:update_progress({
                document = document,
                progress = tostring(progress),
                percentage = percentage,
                device = device,
                device_id = device_id,
            })
        end)
        if ok then
            callback(res.status, res.body)
        else
            logger.dbg("AnxCalibreManagerKoreaderPluginClient:update_progress failure:", res)
            callback(nil, res)
        end
    end)
    self.client:enable("AsyncHTTP", {thread = co})
    coroutine.resume(co)
    if UIManager.looper then UIManager:setInputTimeout() end
    socketutil:reset_timeout()
end
function AnxCalibreManagerKoreaderPluginClient:update_reading_time(
        username,
        password,
        document,
        reading_time,
        date,
        callback)
    self.client:reset_middlewares()
    self.client:enable("Format.JSON")
    self.client:enable("GinClient")
    self.client:enable("KOSyncAuth", {
        username = username,
        userkey = password,
    })
    -- Set *very* tight timeouts to avoid blocking for too long...
    socketutil:set_timeout(PROGRESS_TIMEOUTS[1], PROGRESS_TIMEOUTS[2])
    local co = coroutine.create(function()
        local ok, res = pcall(function()
            return self.client:update_reading_time({
                document = document,
                reading_time = reading_time,
                date = date,
            })
        end)
        if ok then
            callback(res.status == 200, res.body)
        else
            logger.dbg("AnxCalibreManagerKoreaderPluginClient:update_reading_time failure:", res)
            callback(false, res.body)
        end
    end)
    self.client:enable("AsyncHTTP", {thread = co})
    coroutine.resume(co)
    if UIManager.looper then UIManager:setInputTimeout() end
    socketutil:reset_timeout()
end

function AnxCalibreManagerKoreaderPluginClient:get_progress(
        username,
        password,
        document,
        callback)
    self.client:reset_middlewares()
    self.client:enable("Format.JSON")
    self.client:enable("GinClient")
    self.client:enable("KOSyncAuth", {
        username = username,
        userkey = password,
    })
    socketutil:set_timeout(PROGRESS_TIMEOUTS[1], PROGRESS_TIMEOUTS[2])
    local co = coroutine.create(function()
        local ok, res = pcall(function()
            return self.client:get_progress({
                document = document,
            }, { document = document })
        end)
        if ok then
            callback(res.status, res.body)
        else
            logger.dbg("AnxCalibreManagerKoreaderPluginClient:get_progress failure:", res)
            callback(nil, res)
        end
    end)
    self.client:enable("AsyncHTTP", {thread = co})
    coroutine.resume(co)
    if UIManager.looper then UIManager:setInputTimeout() end
    socketutil:reset_timeout()
end

function AnxCalibreManagerKoreaderPluginClient:update_summary(
        username,
        password,
        document,
        rating,
        summary,
        status,
        callback)
    self.client:reset_middlewares()
    self.client:enable("Format.JSON")
    self.client:enable("GinClient")
    self.client:enable("KOSyncAuth", {
        username = username,
        userkey = password,
    })
    socketutil:set_timeout(PROGRESS_TIMEOUTS[1], PROGRESS_TIMEOUTS[2])
    local co = coroutine.create(function()
        local ok, res = pcall(function()
            return self.client:update_summary({
                document = document,
                rating = rating,
                summary = summary,
                status = status,
            })
        end)
        if ok then
            callback(res.status == 200, res.body)
        else
            logger.dbg("AnxCalibreManagerKoreaderPluginClient:update_summary failure:", res)
            callback(false, res.body)
        end
    end)
    self.client:enable("AsyncHTTP", {thread = co})
    coroutine.resume(co)
    if UIManager.looper then UIManager:setInputTimeout() end
    socketutil:reset_timeout()
end

function AnxCalibreManagerKoreaderPluginClient:get_book_details(
        username,
        password,
        document,
        callback)
    self.client:reset_middlewares()
    self.client:enable("Format.JSON")
    self.client:enable("GinClient")
    self.client:enable("KOSyncAuth", {
        username = username,
        userkey = password,
    })
    socketutil:set_timeout(PROGRESS_TIMEOUTS[1], PROGRESS_TIMEOUTS[2])
    local co = coroutine.create(function()
        local ok, res = pcall(function()
            return self.client:get_book_details({
                document = document,
            }, { document = document })
        end)
        if ok then
            callback(res.status == 200, res.body)
        else
            logger.dbg("AnxCalibreManagerKoreaderPluginClient:get_book_details failure:", res)
            callback(false, res.body)
        end
    end)
    self.client:enable("AsyncHTTP", {thread = co})
    coroutine.resume(co)
    if UIManager.looper then UIManager:setInputTimeout() end
    socketutil:reset_timeout()
end

function AnxCalibreManagerKoreaderPluginClient:get_book_stats(
        username,
        password,
        document,
        callback)
    self.client:reset_middlewares()
    self.client:enable("Format.JSON")
    self.client:enable("GinClient")
    self.client:enable("KOSyncAuth", {
        username = username,
        userkey = password,
    })
    socketutil:set_timeout(PROGRESS_TIMEOUTS[1], PROGRESS_TIMEOUTS[2])
    local co = coroutine.create(function()
        local ok, res = pcall(function()
            return self.client:get_book_stats({
                document = document,
            }, { document = document })
        end)
        if ok then
            callback(res.status == 200, res.body)
        else
            logger.dbg("AnxCalibreManagerKoreaderPluginClient:get_book_stats failure:", res)
            callback(false, res.body)
        end
    end)
    self.client:enable("AsyncHTTP", {thread = co})
    coroutine.resume(co)
    if UIManager.looper then UIManager:setInputTimeout() end
    socketutil:reset_timeout()
end

function AnxCalibreManagerKoreaderPluginClient:get_book_stats_sync(username, password, document)
    self.client:reset_middlewares()
    self.client:enable("Format.JSON")
    self.client:enable("GinClient")
    self.client:enable("KOSyncAuth", {
        username = username,
        userkey = password,
    })
    socketutil:set_timeout(PROGRESS_TIMEOUTS[1], PROGRESS_TIMEOUTS[2])
    local ok, res = pcall(function()
        return self.client:get_book_stats({
            document = document,
        }, { document = document })
    end)
    socketutil:reset_timeout()
    if ok and res.status == 200 then
        return true, res.body
    else
        if not ok then
            logger.dbg("AnxCalibreManagerKoreaderPluginClient:get_book_stats_sync failure:", res)
        end
        return false, res and res.body
    end
end

function AnxCalibreManagerKoreaderPluginClient:get_book_details_sync(username, password, document)
    self.client:reset_middlewares()
    self.client:enable("Format.JSON")
    self.client:enable("GinClient")
    self.client:enable("KOSyncAuth", {
        username = username,
        userkey = password,
    })
    socketutil:set_timeout(PROGRESS_TIMEOUTS[1], PROGRESS_TIMEOUTS[2])
    local ok, res = pcall(function()
        return self.client:get_book_details({
            document = document,
        }, { document = document })
    end)
    socketutil:reset_timeout()
    if ok and res.status == 200 then
        return true, res.body
    else
        if not ok then
            logger.dbg("AnxCalibreManagerKoreaderPluginClient:get_book_details_sync failure:", res)
        end
        return false, res and res.body
    end
end

return AnxCalibreManagerKoreaderPluginClient
