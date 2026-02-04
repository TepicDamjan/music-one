
function Footer() {

    const year = new Date().getFullYear();

    return (
        <footer className="flex items-center justify-center py-6 px-4 w-full">

            <div >

                <p className="text-greenPtext text-sm md:text-base font-bold text-center">
                    Copyright © Damjan Tepic {year}
                </p>

            </div>

        </footer>

    );
}

export default Footer;