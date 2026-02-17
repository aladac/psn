USe 
create infra:dns agent boilerplate, role - manage all CF related stuff 
  create following skills:                                                                                                                                 
  - /cf:host:add
  - /cf:tunnel:add
  - /cf:host:del
  - /cf:tunnel:del
  - /cf:tunnel:list
  - /cf:tunnel:info                                                                                                                                        
  - /cf:zone:info                                                                                                                                          
  - /cf:zone:list
  - /cf:pages:list                                                                                                                                         
  - /cf:pages:del
  - /cf:pages:deploy
  - /cf:worker:list                                                                                                                                       
  - /cf:worker:info                                                                                                                                        
  - /cf:worker:del 
  

Commands and skills paths must match:
- commands/cf/host/add.md
- commands/cf/host/add.sh

Every command has to be as automated as possible and feed ready data for the agent to display or process

  wrangler (Workers/Pages)

  wrangler deploy              # Deploy Worker
  wrangler pages deploy        # Deploy Pages
  wrangler d1 / kv / r2        # Storage services
  wrangler tail                # Live logs


  flarectl (DNS/Zones)

  flarectl zone list           # List zones
  flarectl dns list -z domain  # List DNS records
  flarectl dns create          # Create record


  cloudflared (Tunnels)

  cloudflared tunnel list      # List tunnels
  cloudflared tunnel run       # Run tunnel
  cloudflared access           # Access management
  
  Catalog ~/Projects for apps that are being deployed by wrangler
  