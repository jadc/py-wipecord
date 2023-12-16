import sys, aiohttp, asyncio

api = '/api/v9'
RATE_LIMIT_MULTIPLER = 5

async def open_session(token, guild_id, author_id):
    req_headers = { 'Content-Type': 'application/json', 'Authorization': token }
    async with aiohttp.ClientSession('https://discord.com/', headers=req_headers) as session:
        deleted = 0
        user_id = await get_self(session, guild_id, author_id)

        total_results = False
        while not total_results:
            total_results = await get_total_messages(session, guild_id, user_id)

        while True:
            bundle = await get_bundle(session, guild_id, user_id)

            # try again if rate limited
            if not bundle: continue
            # no more msgs to delete, exit loop
            if bundle['total_results'] <= 0: break

            # only delete messages sent by user
            msgs = [x[0] for x in bundle['messages'] if x[0]['author']['id'] == user_id]
            for msg in msgs:
                while True:
                    if await delete_message(session, msg):
                        deleted += 1
                        print(f'{100*(deleted/total_results):.2f}% ({deleted}/{total_results})                             ', end='\r')
                        break
                    else: continue # retry message delete
        print(f'Deleted {deleted} messages')

async def get_self(session, guild_id, author_id):
    async with session.get(f'{api}/users/{author_id}') as resp:
        res = await resp.json()
        print(f"Wiping messages from @{res['username']} in guild {guild_id}")
        return res['id']

async def get_total_messages(session, guild_id, user_id):
    params = {'author_id': user_id, 'include_nsfw': 'true'}
    async with session.get(f"{api}/guilds/{guild_id}/messages/search", params=params) as resp:
        res = await resp.json()

        sleep_for = res.get('retry_after', 0)
        if sleep_for > 0: return await wait(sleep_for)

        return int( res['total_results'] )

async def get_bundle(session, guild_id, user_id):
    params = {'author_id': user_id, 'sort_order': 'asc', 'include_nsfw': 'true'}
    async with session.get(f"{api}/guilds/{guild_id}/messages/search", params=params) as resp:
        res = await resp.json()

        sleep_for = res.get('retry_after', 0) 
        if sleep_for > 0: return await wait(sleep_for)

        return res

async def delete_message(session, msg):
    async with session.delete(f"{api}/channels/{msg['channel_id']}/messages/{msg['id']}") as resp:
        await asyncio.sleep( int(resp.headers.get('Retry-After', 0)) )
        return resp.status == 204
    
async def wait(seconds):
    print(f"Rate limited for {seconds}*{RATE_LIMIT_MULTIPLER} sec...", end='\r')
    await asyncio.sleep( seconds * RATE_LIMIT_MULTIPLER )
    return False

def parse_args(args):
    if(len(args) < 3): return False
    if(len(args) > 4): return False
    if( not args[2].isdigit() ): return False
    if( len(args) == 4 and args[3].isdigit() ): return args[1], args[2], args[3]
    return args[1], args[2], "@me"

if __name__ == '__main__':
    args = parse_args(sys.argv)
    if( args ): asyncio.run( open_session(args[0], args[1], args[2]) )
    else: print(f"Usage: python wipecord.py <token> <guild_id> [author_id]", file=sys.stderr); exit(1)
