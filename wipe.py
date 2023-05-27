import argparse, logging
import aiohttp, asyncio

api = '/api/v9'
async def open_session(args):
    req_headers = { 'Content-Type': 'application/json', 'Authorization': args.token }
    async with aiohttp.ClientSession('https://discord.com/', headers=req_headers) as session:
        # Get user information
        if not args.user: args.user = '@me'
        async with session.get(f'{api}/users/{args.user}') as resp:
            res = await resp.json()
            if(args.verbose): print(res)
            logging.info(f"Wiping messages from @{res['username']} in guild {args.guild}")
            args.user = res['id']

        while True:
            bundle = await get_bundle(session, args.guild, args.user)
            if(args.verbose): print(bundle)

            # try again if rate limited
            if not bundle: continue
            # no more msgs to delete, exit loop
            if len(bundle['total_results']) <= 0: break

            # only delete messages sent by user
            msgs = [x[0] for x in bundle['messages'] if x[0]['author']['id'] == args.user]
            for msg in msgs:
                while True:
                    if await delete_message(session, msg):
                        break
                    else: 
                        logging.error('Failed to delete a message, retrying...')
                        continue # retry message delete
            logging.info(f"{bundle['total_results']} messages remaining")
        logging.info('No messages found!')

async def get_bundle(session, guild_id, user_id):
    params = {'author_id': user_id, 'sort_order': 'asc', 'include_nsfw': 'true'}
    async with session.get(f"{api}/guilds/{guild_id}/messages/search", params=params) as resp:
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

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s | %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')    

    p = argparse.ArgumentParser()
    p.add_argument('token', type=str, help='discord token')
    p.add_argument('guild', type=int, help='guild id')
    p.add_argument('-u', '--user', type=int, help='user id (default is self)')
    p.add_argument('-v', '--verbose', action='store_true', help='verbose output')

    asyncio.run( open_session(p.parse_args()) )
