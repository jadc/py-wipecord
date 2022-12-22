import os, json
import aiohttp, asyncio

config_file = 'config.json'
config = None
api = '/api/v9'

async def open_session():
    req_headers = {
            'Content-Type': 'application/json', 
            'Authorization': config['token']
            }
    async with aiohttp.ClientSession('https://discord.com/', headers=req_headers) as session:
        deleted = 0
        user_id = await get_self(session)
        total_results = await get_total_messages(session, user_id)

        while True:
            bundle = await get_bundle(session, user_id)

            # try again if rate limited
            if not bundle:
                continue

            # no more msgs to delete, exit loop
            if bundle['total_results'] <= 0:
                break

            msgs = [x[0] for x in bundle['messages']]
            for msg in msgs:

                while True:
                    if await delete_message(session, msg):
                        deleted += 1
                        print(f'{100*(deleted/total_results):.2f}% ({deleted}/{total_results})', end='\r')
                        break
                    else:
                        # retry message delete
                        continue

        print(f'Deleted {deleted} messages')

async def get_self(session):
    if config['author_id']:
        print(f"Wiping messages from user with id {config['author_id']}")
        return config['author_id']

    # get own id if none provided
    async with session.get(f'{api}/users/@me') as resp:
        res = await resp.json()
        print(f"Wiping messages from {res['username']}#{res['discriminator']} in guild {config['guild_id']}")
        return res['id']

async def get_total_messages(session, user_id):
    params = {'author_id': user_id, 'include_nsfw': 'true'}
    async with session.get(f"{api}/guilds/{config['guild_id']}/messages/search", params=params) as resp:
        res = await resp.json()
        return int( res['total_results'] )

async def get_bundle(session, user_id):
    params = {'author_id': user_id, 'sort_order': 'asc', 'include_nsfw': 'true'}
    async with session.get(f"{api}/guilds/{config['guild_id']}/messages/search", params=params) as resp:
        res = await resp.json()

        sleep_for = res.get('retry_after', 0)
        if sleep_for > 0:
            await asyncio.sleep( sleep_for )
            return False

        return res

async def delete_message(session, msg):
    async with session.delete(f"{api}/channels/{msg['channel_id']}/messages/{msg['id']}") as resp:
        await asyncio.sleep( int(resp.headers.get('Retry-After', 0)) )
        return resp.status == 204

def load():
    if os.path.isfile(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        with open(config_file, 'w') as f:
            json.dump({'token': '', 'guild_id': '', 'author_id': ''}, f, indent=4)
        return load()

if __name__ == '__main__':
    config = load()
    asyncio.run( open_session() )
