# DNSSEC works by signing DNS records with public-key cryptography. 
# To verify a record, you follow a chain of digital signatures from the child zone up to the "Root" zone.
import dns.resolver
import dns.query
import dns.message

def verify_dnssec(domain):
    # Create a resolver object
    resolver = dns.resolver.Resolver()
    
    # Use a public DNS resolver that supports DNSSEC (like Google or Cloudflare)
    resolver.nameservers = ['8.8.8.8', '1.1.1.1']
    
    # We want to see the 'AD' (Authentic Data) flag in the response
    resolver.set_flags(dns.flags.RD | dns.flags.AD)

    try:
        print(f"Querying DNSSEC status for: {domain}")
        answer = resolver.resolve(domain, 'A')
        
        # Check if the AD flag is present in the response
        is_protected = (answer.response.flags & dns.flags.AD) != 0
        
        if is_protected:
            print(f"SUCCESS: {domain} is verified by DNSSEC.")
        else:
            print(f"WARNING: {domain} responded, but DNSSEC verification failed or is not enabled.")
            
    except Exception as e:
        print(f"Error querying domain: {e}")

if __name__ == "__main__":
    # cloudflare.com and google.com are known to have DNSSEC enabled
    verify_dnssec("cloudflare.com")