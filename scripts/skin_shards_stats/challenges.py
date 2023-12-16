from __future__ import annotations

from typing import Any, Mapping, List

import aiohttp

from common import AluConnector, TabularData


class ChallengeCollectionStats(AluConnector):
    """Challenge Collection Statistics
    
    This feature will print out the amount of skins each champion has and total sum
    of skins calculated from unowned shards.
    
    This is primarly useful for challenges 'That Drip' and 'Need a Bigger Closet'.
    
    Champion skin permanents are disregarded as they are automatically redeemed by client when unowned.
    
    The script will output a table with unowned skin shards being:
    * Unique unowned partial champion skin shards
    and total sum being:
    * Owned champion skins + unique redeemed skin shards
    """
    
    def __init__(self, need_confirmation: bool = False):
        super().__init__(need_confirmation)
    
    async def callback(self) -> str:
        url = "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                champ_json = await resp.json()
                
        skins_by_champion_key = await self.get_skins_by_champion_key(champ_json)
        unowned_shards_by_champion_id = await self.get_unowned_shards_by_champion_id()
        owned_skins_by_champion_id = await self.get_owned_skins_by_champion_id(
            skins_by_champion_key=skins_by_champion_key,
            champ_json=champ_json
        )
        
        table = TabularData()
        table.set_columns(["Champion Name", "Amount of Skins", "Unowned Skin Shards", "Total Sum"])
        for champion_key, skins in skins_by_champion_key.items():
            champion_name = champ_json[champion_key]["name"]
            champion_id = champ_json[champion_key]["id"]
            
            unowned_skin_shards = 0
            if champion_id in unowned_shards_by_champion_id:
                unowned_skin_shards = unowned_shards_by_champion_id[champion_id]
        
            owned_skin_count = 0
            if champion_id in owned_skins_by_champion_id:
                owned_skin_count = owned_skins_by_champion_id[champion_id]
                
            total_sum = owned_skin_count + unowned_skin_shards
            
            table.add_row([champion_name, len(skins), unowned_skin_shards, total_sum])
        
        text = f"Statistics about your challenge collection:\n{table.render()}"
        self.output(text)
        return "Success: Statistics was shown."
    
    async def get_skins_by_champion_key(self, champ_json) -> Mapping[str, List[Any]]:
        """Get mapping `champion_key` -> `list of Meraki champion skins`.
        So we know the skin stats needed for calculation.
        
        Example output:
        >>> {'Aatrox': [{'name': 'Justicar', ...}, ...], 'Ahri': [{'name': 'Arcade', ...}, ...]}
        """
        
        skins_by_champion_id: Mapping[str, List[Any]] = {}
        
        for champion in champ_json.values():
            skins = []
            for skin in champion["skins"]:
                if skin["isBase"]:
                    # Skip base skin for statistics
                    continue
                
                skins.append(skin)
                
            skins_by_champion_id[champion["key"]] = skins
                
        return skins_by_champion_id
    
    async def get_unowned_shards_by_champion_id(self) -> Mapping[int, int]:
        """Get mapping `champion_id` -> `unowned count`.
        Unowned is if the champion shard can be redeemed.
        
        Example output:
        >>> {887: 2, ...}
        """
        
        unowned_shards_by_champion_id: Mapping[int, int] = {}
        loot = await self.get("/lol-loot/v1/player-loot")
        
        for item in await loot.json():
            if item["itemStatus"] != "OWNED": # shard can be redeemed
                if item["disenchantRecipeName"] == "SKIN_RENTAL_disenchant": # normal "partial" champion shard
                    champion_id = item["parentStoreItemId"]
                    
                    if champion_id not in unowned_shards_by_champion_id:
                        unowned_shards_by_champion_id[champion_id] = 1
                    else:
                        unowned_shards_by_champion_id[champion_id] += 1
                    
        return unowned_shards_by_champion_id

    async def get_owned_skins_by_champion_id(self, skins_by_champion_key: Mapping[str, List[Any]], champ_json) -> Mapping[int, int]:
        """Get mapping `champion_id` -> `owned skin count`.
        Owned when the player has the champion skin in their inventory.
        
        Example output:
        >>> {887: 2, ...}
        """
        
        owned_skins_by_champion_id: Mapping[int, int] = {}
        owned_skins = await self.get("/lol-inventory/v2/inventory/CHAMPION_SKIN")
        
        owned_skin_ids = [ x["itemId"] for x in await owned_skins.json()] # Set of owned skin ids
        for champion_key, skins in skins_by_champion_key.items():
            for skin in skins:
                if skin["id"] in owned_skin_ids: # mapped skin is owned
                    champion_id = champ_json[champion_key]["id"]
                    
                    if champion_id not in owned_skins_by_champion_id:
                        owned_skins_by_champion_id[champion_id] = 1
                    else:
                        owned_skins_by_champion_id[champion_id] += 1

        return owned_skins_by_champion_id
        

if __name__ == "__main__":
    ChallengeCollectionStats().start()
    
    
"""
Schema of Meraki champion skin.
{
    "name": "Justicar",
    "id": 266001,
    "isBase": false,
    "availability": "Available",
    "formatName": "Justicar",
    "lootEligible": true,
    "cost": 975,
    "sale": 0,
    "distribution": null,
    "rarity": "NoRarity",
    "chromas": [],
    "lore": "Chief among the Arclight stand the Justicars, sentinels who serve as living embodiments of justice and order. Aatrox embodies power, for it is his martial prowess that holds the chaos back.",
    "release": "2013-06-12",
    "set": [
        "Justicar"
    ],
    "splashPath": "http://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-splashes/266/266001.jpg",
    "uncenteredSplashPath": "http://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-splashes/uncentered/266/266001.jpg",
    "tilePath": "http://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-tiles/266/266001.jpg",
    "loadScreenPath": "https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/assets/characters/aatrox/skins/skin01/aatroxloadscreen_1.jpg",
    "loadScreenVintagePath": null,
    "newEffects": true,
    "newAnimations": true,
    "newRecall": true,
    "newVoice": false,
    "newQuotes": false,
    "voiceActor": [
        "Ramon Tikaram"
    ],
    "splashArtist": [
        "Pan Chengwei"
    ]
}
"""