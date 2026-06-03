from __future__ import annotations

FOLDER_PATTERNS: dict[str, str] = {
    '/Banner-Image/':      'Banner-Image',
    '/product-image/':     'product-image',
    '/client-image/':      'client-image',
    '/Certificate-Image/': 'Certificate-Image',
    '/Leadership_image/':  'Leadership_image',
    '/Testimony_image/':   'Testimony_image',
    '/Claim-process/':     'Claim-process',
    'blog/wp-content':     'blog',
    'career-image':        'career-image',
}


def detect_folder(img_url: str) -> str:
    for pattern, folder in FOLDER_PATTERNS.items():
        if pattern in img_url:
            return folder
    return 'unknown'


def slug_to_title(page_url: str) -> str:
    slug = page_url.rstrip('/').split('/')[-1]
    return slug.replace('-', ' ').replace('_', ' ').title() or 'Salasar Services'


def blog_filename_to_title(img_url: str) -> str:
    filename = img_url.split('/')[-1]
    name = filename.rsplit('.', 1)[0]
    return name.replace('-', ' ').replace('_', ' ').title()


CAPTION_MAP: dict[str, dict[str, str]] = {
    '/': {
        'Banner-Image':      'Salasar Services Insurance Brokers - Pan-India Insurance Brokerage Solutions',
        'product-image':     'Corporate Insurance Products - Property, Aviation, Marine & Liability | Salasar Services',
        'client-image':      'Trusted Client of Salasar Services Insurance Brokers India',
        'Certificate-Image': 'Salasar Services Insurance Brokerage Accreditation & Regulatory Certificate',
        'blog':              'Insurance Industry Insights | Salasar Services Blog',
    },
    '/corporate/aviation-aerospace-insurance': {
        'product-image': 'Aviation & Aerospace Insurance - Aircraft Hull, Liability & Spares | Salasar Services',
    },
    '/corporate/direct-broking/aircraft-hull-insurance': {
        'product-image': 'Aircraft Hull Insurance - Aviation Coverage for Commercial Operators | Salasar Services',
    },
    '/corporate/direct-broking/employee-insurance': {
        'product-image': 'Employee Group Insurance - GMC, GPA & GTL Plans | Salasar Services',
    },
    '/corporate/direct-broking/property-insurance': {
        'product-image': 'Corporate Property Insurance - Asset Protection Solutions | Salasar Services',
    },
    '/corporate/direct-broking/loss-of-profit-contingent-bi': {
        'product-image': 'Loss of Profit & Contingent Business Interruption Insurance | Salasar Services',
    },
    '/corporate/claims-management': {
        'product-image': 'Corporate Insurance Claims Management Services | Salasar Services',
    },
    '/corporate/claims-management/industrial-risks': {
        'product-image':   'Industrial Risk Insurance Claims Management | Salasar Services',
        'Testimony_image': 'Client Testimonial - Industrial Risk Insurance Claims | Salasar Services',
    },
    '/corporate/claims-management/mega-property': {
        'product-image':   'Mega Property Insurance Claims Management | Salasar Services',
        'Testimony_image': 'Client Testimonial - Mega Property Insurance | Salasar Services',
    },
    '/corporate/claims-management/liability-claim': {
        'product-image': 'Liability Insurance Claims Management | Salasar Services',
    },
    '/corporate/claims-management/marine': {
        'product-image': 'Marine Insurance Claims Management | Salasar Services',
    },
    '/corporate/claims-management/miscellaneous-claim': {
        'product-image':     'Miscellaneous Insurance Claims Management - Expert Support | Salasar Services',
        'client-image':      'Satisfied Client - Miscellaneous Insurance Claims | Salasar Services',
        'Certificate-Image': 'Salasar Services Claims Management Accreditation Certificate',
    },
    '/product-details/money-insurance': {
        'Claim-process': 'Money Insurance Claim Process Step | Salasar Services',
        'product-image': 'Money Insurance - Cash in Transit & Safe Coverage | Salasar Services',
    },
    '/product-details/burglary-housebreaking-insurance': {
        'Claim-process': 'Burglary & Housebreaking Insurance Claim Process Step | Salasar Services',
        'product-image': 'Burglary & Housebreaking Insurance - Business Theft Protection | Salasar Services',
    },
    '/product-details/surety-bond-insurance': {
        'product-image': 'Surety Bond Insurance - Contract & Performance Guarantee | Salasar Services',
    },
    '/product-details/trade-credit-insurance': {
        'product-image': 'Trade Credit Insurance - Protect Against Buyer Default | Salasar Services',
    },
    '/product-details/contractor-all-risk': {
        'product-image': 'Contractor All Risk (CAR) Insurance - Construction Project Coverage | Salasar Services',
    },
    '/product-details/erection-all-risk-ear': {
        'product-image': 'Erection All Risk (EAR) Insurance - Plant & Machinery Protection | Salasar Services',
    },
    '/product-details/machinery-breakdown-mbd': {
        'product-image': 'Machinery Breakdown Insurance - Industrial Equipment Coverage | Salasar Services',
    },
    '/industry/agriculture': {
        'product-image':    'Agriculture Insurance Solutions - Crop, Cattle & Farm Risk | Salasar Services',
        'client-image':     'Agriculture Sector Client - Salasar Services Insurance',
        'Leadership_image': 'Salasar Services Agriculture Insurance Expert',
    },
    '/industry/oil-gas': {
        'client-image': 'Oil & Gas Industry Client - Salasar Services Insurance Brokers',
    },
    '/industry/chemical': {
        'client-image':     'Chemical Industry Client - Salasar Services Insurance Brokers',
        'Leadership_image': 'Salasar Services Chemical Industry Insurance Specialist',
    },
    '/industry/power': {
        'client-image':     'Power Sector Client - Salasar Services Insurance Brokers',
        'Leadership_image': 'Salasar Services Power Sector Insurance Expert',
    },
    '/industry/tea': {
        'product-image':    'Tea Industry Insurance - Estate, Crop & Workers Coverage | Salasar Services',
        'Leadership_image': 'Salasar Services Tea Industry Insurance Specialist',
    },
    '/industry/sugar': {
        'client-image':     'Sugar Industry Client - Salasar Services Insurance Brokers',
        'Leadership_image': 'Salasar Services Sugar Industry Insurance Expert',
    },
    '/industry/iron-steel': {
        'Testimony_image': 'Iron & Steel Industry Client Testimonial | Salasar Services',
    },
    '/industry/logistics': {
        'Leadership_image': 'Salasar Services Logistics Insurance Expert',
    },
    '/industry/automobile': {
        'product-image': 'Automobile Industry Insurance - Fleet & Liability Coverage | Salasar Services',
    },
    '/corporate/rural-insurance-solutions/crop-weather': {
        'Claim-process':    'Crop & Weather Insurance Claim Process | Salasar Services',
        'Leadership_image': 'Salasar Services Rural Insurance Expert - Leadership Profile',
    },
    '/retail/life-insurance': {
        'Leadership_image': 'Salasar Services Life Insurance Expert - Advisory Team',
    },
    '/retail/life-insurance/whole-life-insurance': {
        'Leadership_image': 'Salasar Services Whole Life Insurance Advisor',
    },
    '/career': {
        'Banner-Image':    'Life at Salasar Services - Work Culture & Employee Wellbeing',
        'Testimony_image': 'Employee Testimonial - Life at Salasar Services Insurance Brokers',
    },
}

FOLDER_FALLBACKS: dict[str, object] = {
    'Banner-Image':      lambda s: f'{s} - Insurance Services Banner | Salasar Services',
    'product-image':     lambda s: f'{s} - Insurance Product | Salasar Services',
    'client-image':      lambda _: 'Trusted Client of Salasar Services Insurance Brokers',
    'Certificate-Image': lambda _: 'Salasar Services Insurance Regulatory Certificate & Accreditation',
    'Leadership_image':  lambda s: f'Salasar Services Leadership - {s} Insurance Expert',
    'Testimony_image':   lambda s: f'Client Testimonial - {s} | Salasar Services',
    'Claim-process':     lambda s: f'{s} Claim Process | Salasar Services',
    'blog':              lambda s: f'{s} - Insurance Industry Article | Salasar Services',
    'career-image':      lambda _: 'Careers at Salasar Services Insurance Brokers',
    'unknown':           lambda s: f'{s} | Salasar Services Insurance Brokers',
}


def generate_caption(img_url: str, page_path: str) -> str:
    folder = detect_folder(img_url)
    if folder == 'blog':
        return f'{blog_filename_to_title(img_url)} - Insurance Industry Insights | Salasar Services'
    page_map = CAPTION_MAP.get(page_path, {})
    if folder in page_map:
        return page_map[folder]
    slug = slug_to_title(page_path)
    return FOLDER_FALLBACKS.get(folder, FOLDER_FALLBACKS['unknown'])(slug)
