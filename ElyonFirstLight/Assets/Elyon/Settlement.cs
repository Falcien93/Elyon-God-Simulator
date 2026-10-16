using System;
using UnityEngine;

namespace Elyon
{
    public enum Labor
    {
        Gather,
        Hunt,
        Farm,
        Smith,
        Tend,
        Teach,
        Guard,
        Follow,
        Engine,
        Wire,
        Keep,
    }

    public enum ToolKind
    {
        Hands,
        Axe,
        Hoe,
        Hammer,
    }

    public enum Season
    {
        Spring = 0,
        Summer = 1,
        Autumn = 2,
        Winter = 3,
    }

    public enum Sky
    {
        Clear = 0,
        Rain = 1,
        Drought = 2,
        Flood = 3,
    }

    [Serializable]
    public class Settlement
    {
        public string id = "eden";
        public string placeName = "the fire";
        public float hearthX = 150f;
        public float hearthZ = 100f;
        public float fruit = 18f;
        public float meat;
        public float grain;
        public float water = 24f;
        public float wood = 4f;
        public float ore;
        public float faith = 36f;
        public int tents;
        public int houses;
        public int fields;
        public int metalTools;
        public bool smithy;
        public bool hall;
        public bool temple;
        public bool palisade;
        public bool letters;
        public bool press;
        public bool mill;
        public bool millOn = true;
        public bool engine;
        public bool engineOn;
        public float drive;
        public float power;
        public bool lights;
        public bool abandoned;
        public bool dread;
        public bool pactStay;
        public bool raided;
        public bool lawKept;
        public bool willRaid;
        public int herd;
        public float fish;
        public string herdName = "";
        public string fishName = "";
        public Sky sky = Sky.Clear;

        public float Meals => fruit + meat + grain + fish;

        public Vector3 Hearth => new Vector3(hearthX, 0f, hearthZ);

        public bool TakeMeal(float amount)
        {
            if (Meals + 0.001f < amount) return false;
            float left = amount;
            float fromFruit = Mathf.Min(fruit, left);
            fruit -= fromFruit;
            left -= fromFruit;
            float fromMeat = Mathf.Min(meat, left);
            meat -= fromMeat;
            left -= fromMeat;
            float fromFish = Mathf.Min(fish, left);
            fish -= fromFish;
            left -= fromFish;
            grain = Mathf.Max(0f, grain - left);
            return true;
        }

        public bool TakeWater(float amount)
        {
            if (water < amount) return false;
            water -= amount;
            return true;
        }

        public void Receive(Settlement other)
        {
            fruit += other.fruit;
            meat += other.meat;
            grain += other.grain;
            water += other.water;
            wood += other.wood;
            ore += other.ore;
            fish += other.fish;
            herd = Mathf.Min(6, herd + other.herd);
            if (herd > 0 && string.IsNullOrEmpty(herdName) && !string.IsNullOrEmpty(other.herdName))
            {
                herdName = other.herdName;
                other.herdName = "";
            }
            if (fish >= 1f && string.IsNullOrEmpty(fishName) && !string.IsNullOrEmpty(other.fishName))
            {
                fishName = other.fishName;
                other.fishName = "";
            }
            faith = Mathf.Max(faith, other.faith);
            other.fruit = 0f;
            other.fish = 0f;
            other.herd = 0;
            other.meat = 0f;
            other.grain = 0f;
            other.water = 0f;
            other.wood = 0f;
            other.ore = 0f;
        }
    }
}
