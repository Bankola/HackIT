<img width="256" height="256" alt="icon_128x128@2x" src="https://cdn.forbes.ru/forbes-static/new/2024/09/T1-1-kopia2-66f13ec658c5e.jpg" />
#PingTower

Современные компании критически зависят от бесперебойной работы своих веб-сервисов, поскольку каждая минута простоя может обходиться бизнесу в значительные финансовые потери, особенно для компаний электронной коммерции, финансовых сервисов и SaaS-платформ. Регулярно возникающие сбои из-за технических неисправностей, перегрузок сервера, проблем с сетевой инфраструктурой или DDoS-атак приводят к потере клиентов, снижению доверия к бренду и прямым убыткам от недоступности сервисов. Существующие подходы к мониторингу часто основаны на ручных проверках или базовых инструментах, которые не обеспечивают комплексного контроля и быстрого реагирования на проблемы. Многие компании узнают о сбоях только после жалоб пользователей, что значительно усугубляет последствия инцидентов и увеличивает время восстановления. Отсутствие автоматизированного мониторинга с детальной аналитикой и гибкой системой уведомлений не позволяет техническим командам проактивно предотвращать проблемы и оперативно реагировать на возникающие сбои, что в конечном итоге негативно сказывается на пользовательском опыте и репутации компании.

Наша команда разработала комплексную систему мониторинга веб-сервисов, которая обеспечивает непрерывное отслеживание доступности и производительности цифровых ресурсов в режиме 24/7. Система включает мощный планировщик проверок, построенный на базе Cron-подобной архитектуры, который позволяет настраивать гибкие расписания мониторинга для различных типов ресурсов с возможностью определения интервалов проверки от нескольких секунд до часов в зависимости от критичности сервиса. 


## Features

- **Dual Transport Architecture**: Bluetooth mesh for offline + Nostr protocol for internet-based messaging
- **Location-Based Channels**: Geographic chat rooms using geohash coordinates over global Nostr relays
- **Intelligent Message Routing**: Automatically chooses best transport (Bluetooth → Nostr fallback)
- **Decentralized Mesh Network**: Automatic peer discovery and multi-hop message relay over Bluetooth LE
- **Privacy First**: No accounts, no phone numbers, no persistent identifiers
- **Private Message End-to-End Encryption**: [Noise Protocol](http://noiseprotocol.org) for mesh, NIP-17 for Nostr
- **IRC-Style Commands**: Familiar `/slap`, `/msg`, `/who` style interface
- **Universal App**: Native support for iOS and macOS
- **Emergency Wipe**: Triple-tap to instantly clear all data
- **Performance Optimizations**: LZ4 message compression, adaptive battery modes, and optimized networking

## [Technical Architecture](https://deepwiki.com/permissionlesstech/bitchat)

BitChat uses a **hybrid messaging architecture** with two complementary transport layers:

### Bluetooth Mesh Network (Offline)

- **Local Communication**: Direct peer-to-peer within Bluetooth range
- **Multi-hop Relay**: Messages route through nearby devices (max 7 hops)
- **No Internet Required**: Works completely offline in disaster scenarios
- **Noise Protocol Encryption**: End-to-end encryption with forward secrecy
- **Binary Protocol**: Compact packet format optimized for Bluetooth LE constraints
- **Automatic Discovery**: Peer discovery and connection management
- **Adaptive Power**: Battery-optimized duty cycling

### Nostr Protocol (Internet)

- **Global Reach**: Connect with users worldwide via internet relays
- **Location Channels**: Geographic chat rooms using geohash coordinates
- **290+ Relay Network**: Distributed across the globe for reliability
- **NIP-17 Encryption**: Gift-wrapped private messages for internet privacy
- **Ephemeral Keys**: Fresh cryptographic identity per geohash area

### Channel Types

#### `mesh #bluetooth`

- **Transport**: Bluetooth Low Energy mesh network
- **Scope**: Local devices within multi-hop range
- **Internet**: Not required
- **Use Case**: Offline communication, protests, disasters, remote areas

#### Location Channels (`block #dr5rsj7`, `neighborhood #dr5rs`, `country #dr`)

- **Transport**: Nostr protocol over internet
- **Scope**: Geographic areas defined by geohash precision
  - `block` (7 chars): City block level
  - `neighborhood` (6 chars): District/neighborhood
  - `city` (5 chars): City level
  - `province` (4 chars): State/province
  - `region` (2 chars): Country/large region
- **Internet**: Required (connects to Nostr relays)
- **Use Case**: Location-based community chat, local events, regional discussions

### Direct Message Routing

Private messages use **intelligent transport selection**:

1. **Bluetooth First** (preferred when available)

   - Direct connection with established Noise session
   - Fastest and most private option

2. **Nostr Fallback** (when Bluetooth unavailable)

   - Uses recipient's Nostr public key
   - NIP-17 gift-wrapping for privacy
   - Routes through global relay network

3. **Smart Queuing** (when neither available)
   - Messages queued until transport becomes available
   - Automatic delivery when connection established

For detailed protocol documentation, see the [Technical Whitepaper](WHITEPAPER.md).

## Setup

### Option 1: Using Xcode

   ```bash
   cd bitchat
   open bitchat.xcodeproj
   ```

   To run on a device there're a few steps to prepare the code:
   - Clone the local configs: `cp Configs/Local.xcconfig.example Configs/Local.xcconfig`
   - Add your Developer Team ID into the newly created `Configs/Local.xcconfig`
      - Bundle ID would be set to `chat.bitchat.<team_id>` (unless you set to something else)
   - Entitlements need to be updated manually (TODO: Automate):
      - Search and replace `group.chat.bitchat` with `group.<your_bundle_id>` (e.g. `group.chat.bitchat.ABC123`)

### Option 2: Using `just`

   ```bash
   brew install just
   ```

Want to try this on macos: `just run` will set it up and run from source.
Run `just clean` afterwards to restore things to original state for mobile app building and development.
